"""DataUpdateCoordinator for the Xiaomi Smart Pet Feeder 2."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import homeassistant.util.dt as dt_util

from xiaomi_feeder_2 import (
    FeederStatus,
    ScheduleMeal,
    SchedulePlan,
    XiaomiFeeder,
    XiaomiFeederConnectionError,
    XiaomiFeederDeviceError,
    XiaomiFeederError,
)

from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_FEED_COMPLETED,
    FAST_SCAN_INTERVAL,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class FeederCoordinatorData:
    """Structure holding all device telemetry, schedules, and event history."""
    status: FeederStatus
    schedule: SchedulePlan
    next_feed_time: Optional[datetime] = None
    next_feed_portions: Optional[int] = None
    is_next_feed_skipped: bool = False
    skip_meals_count: int = 0
    feed_history: List[Dict[str, Any]] = field(default_factory=list)
    last_feed_event: Optional[Dict[str, Any]] = None


class XiaomiFeederCoordinator(DataUpdateCoordinator[FeederCoordinatorData]):
    """Coordinator to manage polling and commands for the Xiaomi Pet Feeder 2."""

    def __init__(
        self,
        hass: HomeAssistant,
        ip: str,
        token: str,
        name: str,
        entry_id: str,
    ) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{ip}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.ip = ip
        self.token = token
        self.device_name = name
        self.entry_id = entry_id
        self.client = XiaomiFeeder(ip, token)

        # Storage for persistent state (master schedule template, history)
        self._store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry_id}")
        self._stored_data: Dict[str, Any] = {}

        # Internal state tracking
        self._master_schedule: Optional[SchedulePlan] = None
        self._skip_next_meal: bool = False
        self._skip_meals_count: int = 0
        self._skipped_meal_time: Optional[datetime] = None
        self._prev_is_busy: bool = False
        self._feed_in_progress_start: Optional[datetime] = None
        self._prev_daily_eaten: Optional[int] = None
        self._manual_portions: int = 1

    @property
    def manual_portions(self) -> int:
        """Portions configured on manual feed slider."""
        return self._manual_portions

    @manual_portions.setter
    def manual_portions(self, value: int) -> None:
        self._manual_portions = max(1, min(30, int(value)))
        self._stored_data["manual_portions"] = self._manual_portions
        self.hass.async_create_task(self._async_save_storage())

    async def async_set_manual_portions(self, portions: int) -> None:
        """Set manual portions in HA and sync to feeder hardware."""
        self._manual_portions = max(1, min(30, int(portions)))
        self._stored_data["manual_portions"] = self._manual_portions
        await self._async_save_storage()
        try:
            await self.hass.async_add_executor_job(self.client.set_target_portions, self._manual_portions)
        except Exception as err:
            _LOGGER.debug("Could not push target_portions to feeder: %s", err)

    async def async_load_storage(self) -> None:
        """Load persistent data from Home Assistant storage."""
        loaded = await self._store.async_load()
        if isinstance(loaded, dict):
            self._stored_data = loaded
            self._manual_portions = self._stored_data.get("manual_portions", 1)
        else:
            self._stored_data = {
                "manual_portions": 1,
                "feed_history": [],
                "master_schedule_raw": "",
            }
            await self._store.async_save(self._stored_data)

    async def _async_save_storage(self) -> None:
        """Persist data to storage."""
        await self._store.async_save(self._stored_data)

    async def _async_update_data(self) -> FeederCoordinatorData:
        """Fetch all data from the feeder."""
        try:
            # 1. Fetch hardware status and schedule
            status: FeederStatus = await self.hass.async_add_executor_job(self.client.status)
            raw_schedule = await self.hass.async_add_executor_job(self.client.get_hardware_schedule)
            schedule = self._parse_schedule(raw_schedule)

            # Adjust polling interval if dispensing is active
            if status.is_busy:
                self.update_interval = timedelta(seconds=FAST_SCAN_INTERVAL)
            else:
                self.update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

            # 2. Update Master Schedule Template in storage if not set or externally modified
            if not self._stored_data.get("master_schedule_raw") and schedule.raw_string:
                self._stored_data["master_schedule_raw"] = schedule.raw_string
                await self._async_save_storage()

            # 3. Auto-sync manual portions to feeder hardware if feeder rebooted / desynced
            if status.target_feeding_portions and status.target_feeding_portions != self._manual_portions:
                _LOGGER.debug(
                    "Feeder target portions (%s) differs from slider setting (%s). Re-syncing...",
                    status.target_feeding_portions,
                    self._manual_portions,
                )
                try:
                    await self.hass.async_add_executor_job(self.client.set_target_portions, self._manual_portions)
                except Exception as err:
                    _LOGGER.debug("Could not re-sync target_portions to feeder: %s", err)

            now = dt_util.now()

            # 3. Supervisor: Calculate next scheduled feeding & handle Skip Next Meal
            next_time, next_portions = self._calculate_next_feeding(schedule.meals)

            # Check if an active skipped meal timestamp has now passed
            if self._skipped_meal_time and now > self._skipped_meal_time:
                _LOGGER.info("Skipped meal time %s has passed. Restoring master schedule", self._skipped_meal_time)
                self._skipped_meal_time = None
                self._skip_next_meal = False
                if self._skip_meals_count > 0:
                    self._skip_meals_count -= 1

                # Restore master schedule to EEPROM
                master_raw = self._stored_data.get("master_schedule_raw")
                if master_raw:
                    await self.hass.async_add_executor_job(self._write_raw_hardware_schedule_sync, master_raw)
                    raw_sched = await self.hass.async_add_executor_job(self.client.get_hardware_schedule)
                    schedule = self._parse_schedule(raw_sched)
                    next_time, next_portions = self._calculate_next_feeding(schedule.meals)

            # 4. Detect Feed Events and Build History
            feed_history = self._stored_data.get("feed_history", [])
            last_feed_event = feed_history[-1] if feed_history else None

            if self._prev_is_busy and not status.is_busy:
                # Motor just finished dispensing
                event_data = {
                    "timestamp": now.isoformat(),
                    "time_str": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "portions": self._manual_portions,
                    "bowl_weight": status.bowl_food_weight,
                    "daily_eaten": status.daily_eaten_weight,
                    "type": "dispense_finished",
                }
                feed_history.append(event_data)
                if len(feed_history) > 50:
                    feed_history = feed_history[-50:]
                self._stored_data["feed_history"] = feed_history
                await self._async_save_storage()
                last_feed_event = event_data

                # Fire event on Home Assistant event bus
                self.hass.bus.async_fire(EVENT_FEED_COMPLETED, event_data)

            self._prev_is_busy = status.is_busy
            self._prev_daily_eaten = status.daily_eaten_weight

            return FeederCoordinatorData(
                status=status,
                schedule=schedule,
                next_feed_time=next_time,
                next_feed_portions=next_portions,
                is_next_feed_skipped=self._skip_next_meal,
                skip_meals_count=self._skip_meals_count,
                feed_history=feed_history,
                last_feed_event=last_feed_event,
            )

        except (XiaomiFeederConnectionError, XiaomiFeederDeviceError, XiaomiFeederError) as err:
            raise UpdateFailed(f"Error communicating with Xiaomi Feeder: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching Xiaomi Feeder data: %s", err)
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def _parse_schedule(self, data: Any) -> SchedulePlan:
        """Parse raw schedule dict or SchedulePlan into SchedulePlan dataclass."""
        if isinstance(data, SchedulePlan):
            return data
        if not isinstance(data, dict):
            return SchedulePlan(enabled=False, meals=[], raw_string="")

        meals_list: List[ScheduleMeal] = []
        for m in data.get("meals", []):
            if isinstance(m, ScheduleMeal):
                meals_list.append(m)
            elif isinstance(m, dict):
                meals_list.append(
                    ScheduleMeal(
                        time=m.get("time", "00:00"),
                        portions=int(m.get("portions", 1)),
                        repeat=int(m.get("repeat", 0)),
                        raw=str(m.get("raw", "")),
                    )
                )

        return SchedulePlan(
            enabled=bool(data.get("enabled", False)),
            meals=meals_list,
            raw_string=str(data.get("raw_string", "")),
        )

    def _calculate_next_feeding(self, meals: List[ScheduleMeal]) -> tuple[Optional[datetime], Optional[int]]:
        """Calculate the next upcoming meal datetime and portions from schedule meals."""
        if not meals:
            return None, None

        now = dt_util.now()
        current_weekday = now.weekday()  # Monday is 0, Sunday is 6
        candidates: List[tuple[datetime, int]] = []

        for meal in meals:
            try:
                hour, minute = map(int, meal.time.split(":"))
            except Exception:
                continue

            # Check next 7 days
            for day_offset in range(8):
                check_date = now.date() + timedelta(days=day_offset)
                check_weekday = check_date.weekday()
                
                # Check repeat bitmask: bit 0 = Mon (1), bit 1 = Tue (2)... bit 6 = Sun (64)
                # repeat == 0 means one-time today
                repeat_mask = meal.repeat
                day_bit = 1 << check_weekday
                is_scheduled_for_day = (repeat_mask == 1) or (repeat_mask == 127) or (repeat_mask == 0 and day_offset == 0) or bool(repeat_mask & day_bit)

                if is_scheduled_for_day:
                    candidate_dt = dt_util.as_local(datetime(check_date.year, check_date.month, check_date.day, hour, minute))
                    if candidate_dt > now:
                        candidates.append((candidate_dt, meal.portions))
                        break

        if not candidates:
            return None, None

        candidates.sort(key=lambda x: x[0])
        return candidates[0][0], candidates[0][1]

    # --------------------------------------------------------------------------
    # Control Actions
    # --------------------------------------------------------------------------
    async def async_feed(self, portions: Optional[int] = None) -> None:
        """Trigger manual feeding."""
        count = portions if portions is not None else self._manual_portions
        await self.hass.async_add_executor_job(self.client.feed, count)
        await self.async_request_refresh()

    async def async_calibrate_scale(self) -> None:
        """Tare / calibrate bowl scale load cell."""
        await self.hass.async_add_executor_job(self.client.calibrate_scale)
        await self.async_request_refresh()

    async def async_set_target_portions(self, portions: int) -> None:
        """Set RAM default manual portions."""
        await self.hass.async_add_executor_job(self.client.set_target_portions, portions)
        await self.async_request_refresh()

    async def async_set_child_lock(self, locked: bool) -> None:
        """Lock or unlock top physical button."""
        await self.hass.async_add_executor_job(self.client.set_child_lock, locked)
        await self.async_request_refresh()

    async def async_set_screen_auto_sleep(self, enabled: bool) -> None:
        """Set screen auto-sleep."""
        await self.hass.async_add_executor_job(self.client.set_screen_auto_sleep, enabled)
        await self.async_request_refresh()

    async def async_set_screen_progress_display(self, enabled: bool) -> None:
        """Set screen light-up during feeding."""
        await self.hass.async_add_executor_job(self.client.set_screen_progress_display, enabled)
        await self.async_request_refresh()

    async def async_set_screen_display_mode(self, mode: str) -> None:
        """Set screen display mode ('left', 'eaten', 'percentage')."""
        await self.hass.async_add_executor_job(self.client.set_screen_display, mode)
        await self.async_request_refresh()

    async def async_set_anti_stacking(self, enabled: bool) -> None:
        """Set anti-stacking motor rotation."""
        await self.hass.async_add_executor_job(self.client.set_anti_stacking, enabled)
        await self.async_request_refresh()

    async def async_set_grain_compensation(self, enabled: bool) -> None:
        """Set grain compensation."""
        await self.hass.async_add_executor_job(self.client.set_grain_compensation, enabled)
        await self.async_request_refresh()

    async def async_set_refill_reminder(self, enabled: bool, interval_hours: int = 6) -> None:
        """Configure refill reminder."""
        await self.hass.async_add_executor_job(self.client.set_refill_reminder, enabled, interval_hours)
        await self.async_request_refresh()

    async def async_clear_refill_alert(self) -> None:
        """Clear refill alert."""
        await self.hass.async_add_executor_job(self.client.clear_refill_alert)
        await self.async_request_refresh()

    async def async_set_intake_alarm(self, enabled: bool, threshold_pct: int = 10) -> None:
        """Configure low intake alert."""
        await self.hass.async_add_executor_job(self.client.set_intake_alarm, enabled, threshold_pct)
        await self.async_request_refresh()

    async def async_clear_intake_alert(self) -> None:
        """Clear low intake alert."""
        await self.hass.async_add_executor_job(self.client.clear_intake_alert)
        await self.async_request_refresh()

    async def async_enable_hardware_schedule(self, enabled: bool) -> None:
        """Master toggle for hardware schedule."""
        await self.hass.async_add_executor_job(self.client.enable_hardware_schedule, enabled)
        await self.async_request_refresh()

    def _write_raw_hardware_schedule_sync(self, raw_str: str) -> Any:
        """Write raw schedule string to EEPROM with fallback to direct MIoT action."""
        if hasattr(self.client, "write_raw_hardware_schedule"):
            return self.client.write_raw_hardware_schedule(raw_str)

        clean = raw_str.strip()
        if not clean or clean == "0" or clean == "[0]":
            return self.client.clear_hardware_schedule()

        if clean.startswith("[") and clean.endswith("]"):
            payload_str = clean
        else:
            payload_str = f"[1,{clean}]"

        from .const import FeederAIID, FeederPIID, FeederSIID
        res = self.client.call_action(
            siid=FeederSIID.CUSTOM,
            aiid=FeederAIID.UPDATE_FEEDING_PROGRAM,
            in_params=[{"piid": FeederPIID.FEEDING_PROGRAM, "value": payload_str}],
        )
        try:
            self.client.set_property(
                siid=FeederSIID.CUSTOM,
                piid=FeederPIID.FEEDING_PLAN_SWITCH,
                value=1,
            )
        except Exception:
            pass
        return res

    @staticmethod
    def _mask_meal_raw(raw: str) -> str:
        """Disable a meal by zeroing its status field (last 2 digits: 01=active, 00=disabled)."""
        if not raw or len(raw) < 8:
            return raw
        return raw[:6] + "00"

    async def async_write_hardware_schedule(self, raw_schedule_str: str) -> None:
        """Write raw schedule string to EEPROM and update master template."""
        clean_str = raw_schedule_str.strip()
        await self.hass.async_add_executor_job(self._write_raw_hardware_schedule_sync, clean_str)
        self._stored_data["master_schedule_raw"] = clean_str
        await self._async_save_storage()
        await self.async_request_refresh()

    async def async_clear_hardware_schedule(self) -> None:
        """Clear EEPROM hardware schedule."""
        await self.hass.async_add_executor_job(self.client.clear_hardware_schedule)
        self._stored_data["master_schedule_raw"] = ""
        await self._async_save_storage()
        await self.async_request_refresh()

    async def async_set_skip_next_meal(self, skip: bool, count: int = 1) -> None:
        """Dynamically skip the next upcoming meal without losing the master schedule."""
        if skip:
            if not self.data or not self.data.next_feed_time:
                _LOGGER.warning("Cannot skip next meal: No upcoming meal scheduled.")
                return

            self._skip_next_meal = True
            self._skip_meals_count = max(1, count)
            self._skipped_meal_time = self.data.next_feed_time

            # Create an EEPROM payload that temporarily omits the next meal
            target_time_str = self.data.next_feed_time.strftime("%H:%M")
            raw_payload = ",".join(
                self._mask_meal_raw(m.raw) if m.time == target_time_str else m.raw
                for m in self.data.schedule.meals
            ) or "0"
            _LOGGER.info("Temporarily disabling meal at %s. Writing payload: %s", target_time_str, raw_payload)
            await self.hass.async_add_executor_job(self._write_raw_hardware_schedule_sync, raw_payload)
        else:
            self._skip_next_meal = False
            self._skip_meals_count = 0
            self._skipped_meal_time = None
            master_raw = self._stored_data.get("master_schedule_raw", "")
            if master_raw:
                _LOGGER.info("Restoring master schedule to EEPROM: %s", master_raw)
                await self.hass.async_add_executor_job(self._write_raw_hardware_schedule_sync, master_raw)

        await self.async_request_refresh()
