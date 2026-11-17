"""Sensor platform for Xiaomi Smart Pet Feeder 2."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfMass, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_MODEL, DOMAIN
from .coordinator import FeederCoordinatorData, XiaomiFeederCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Xiaomi Feeder sensors based on a config entry."""
    coordinator: XiaomiFeederCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors: list[SensorEntity] = [
        XiaomiFeederBowlWeightSensor(coordinator, entry),
        XiaomiFeederDailyEatenSensor(coordinator, entry),
        XiaomiFeederDailyEatenCalculatedSensor(coordinator, entry),
        XiaomiFeederLastMealSensor(coordinator, entry),
        XiaomiFeederPreviousMealSensor(coordinator, entry),
        XiaomiFeederLastEatingSensor(coordinator, entry),
        XiaomiFeederEatingHistorySensor(coordinator, entry),
        XiaomiFeederTargetPortionsSensor(coordinator, entry),
        XiaomiFeederNextFeedSensor(coordinator, entry),
        XiaomiFeederScheduleCountSensor(coordinator, entry),
        XiaomiFeederLastFeedEventSensor(coordinator, entry),
        XiaomiFeederFeedHistorySensor(coordinator, entry),
        XiaomiFeederTimezoneSensor(coordinator, entry),
        XiaomiFeederDailyProgressSensor(coordinator, entry),
    ]

    async_add_entities(sensors)



class XiaomiFeederBaseSensor(CoordinatorEntity[XiaomiFeederCoordinator], SensorEntity):
    """Base class for Xiaomi Feeder sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        """Initialize base sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=coordinator.device_name,
            manufacturer="Xiaomi",
            model=DEFAULT_MODEL,
        )


class XiaomiFeederBowlWeightSensor(XiaomiFeederBaseSensor):
    """Real-time bowl food weight scale sensor."""

    _attr_translation_key = "bowl_weight"
    _attr_native_unit_of_measurement = UnitOfMass.GRAMS
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:scale"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_bowl_weight"
        self._attr_name = "Bowl Food Weight"

    @property
    def native_value(self) -> Optional[int]:
        if self.coordinator.data and self.coordinator.data.status:
            return self.coordinator.data.status.bowl_food_weight
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {"fast_polling": self.coordinator.is_fast_weight_polling()}


class XiaomiFeederDailyEatenSensor(XiaomiFeederBaseSensor):
    """Daily cumulative eaten food weight sensor."""

    _attr_translation_key = "daily_eaten"
    _attr_native_unit_of_measurement = UnitOfMass.GRAMS
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:food-drumstick"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_daily_eaten"
        self._attr_name = "Daily Eaten Weight"

    @property
    def native_value(self) -> Optional[int]:
        if self.coordinator.data and self.coordinator.data.status:
            return self.coordinator.data.status.daily_eaten_weight
        return None


class XiaomiFeederLastMealSensor(XiaomiFeederBaseSensor):
    """Grams consumed in the most recent meal session."""

    _attr_translation_key = "last_meal_intake"
    _attr_native_unit_of_measurement = UnitOfMass.GRAMS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:food"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_meal_intake"
        self._attr_name = "Last Meal Intake"

    @property
    def native_value(self) -> Optional[int]:
        if self.coordinator.data and self.coordinator.data.status:
            return self.coordinator.data.status.last_meal_intake
        return None


class XiaomiFeederPreviousMealSensor(XiaomiFeederBaseSensor):
    """Grams consumed in the prior meal session."""

    _attr_translation_key = "previous_meal_intake"
    _attr_native_unit_of_measurement = UnitOfMass.GRAMS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:history"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_previous_meal_intake"
        self._attr_name = "Previous Meal Intake"

    @property
    def native_value(self) -> Optional[int]:
        if self.coordinator.data and self.coordinator.data.status:
            return self.coordinator.data.status.previous_meal_intake
        return None


class XiaomiFeederNextFeedSensor(XiaomiFeederBaseSensor):
    """Next scheduled feeding time timestamp sensor."""

    _attr_translation_key = "next_feeding"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-fast"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_feeding"
        self._attr_name = "Next Feeding"

    @property
    def native_value(self) -> Optional[datetime]:
        if self.coordinator.data:
            return self.coordinator.data.next_feed_time
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        attrs: Dict[str, Any] = {}
        if self.coordinator.data:
            attrs["portions"] = self.coordinator.data.next_feed_portions
            attrs["is_skipped"] = self.coordinator.data.is_next_feed_skipped
            attrs["skip_count"] = self.coordinator.data.skip_meals_count
        return attrs


class XiaomiFeederScheduleCountSensor(XiaomiFeederBaseSensor):
    """Count of configured hardware schedule meals."""

    _attr_translation_key = "schedule_count"
    _attr_icon = "mdi:calendar-multiselect"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_schedule_count"
        self._attr_name = "Hardware Schedule Count"

    @property
    def native_value(self) -> Optional[int]:
        if self.coordinator.data and self.coordinator.data.status:
            return self.coordinator.data.status.hardware_schedule_count
        return None


class XiaomiFeederLastFeedEventSensor(XiaomiFeederBaseSensor):
    """Summary of the last completed feeding event."""

    _attr_translation_key = "last_feed_event"
    _attr_icon = "mdi:check-circle-outline"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_feed_event"
        self._attr_name = "Last Feed Event"

    @property
    def native_value(self) -> Optional[str]:
        if self.coordinator.data and self.coordinator.data.last_feed_event:
            return self.coordinator.data.last_feed_event.get("time_str", "Unknown")
        return "None"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        if self.coordinator.data and self.coordinator.data.last_feed_event:
            return self.coordinator.data.last_feed_event
        return {}


class XiaomiFeederFeedHistorySensor(XiaomiFeederBaseSensor):
    """Feed history sensor holding an array of recent feeding events for timeline visualization."""

    _attr_translation_key = "feed_history"
    _attr_icon = "mdi:format-list-bulleted-type"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_feed_history"
        self._attr_name = "Feeding History"

    @property
    def native_value(self) -> int:
        if self.coordinator.data:
            return len(self.coordinator.data.feed_history)
        return 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        if self.coordinator.data:
            return {"history": self.coordinator.data.feed_history}
        return {"history": []}


class XiaomiFeederTimezoneSensor(XiaomiFeederBaseSensor):
    """Device internal RTC timezone offset."""

    _attr_translation_key = "timezone_offset"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:map-clock"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_timezone_offset"
        self._attr_name = "Device Timezone Offset (sec)"

    @property
    def native_value(self) -> Optional[int]:
        if self.coordinator.data and self.coordinator.data.status:
            return self.coordinator.data.status.device_timezone_sec
        return None


class XiaomiFeederDailyProgressSensor(XiaomiFeederBaseSensor):
    """Daily schedule feeding plan progress percentage."""

    _attr_translation_key = "daily_progress"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:chart-arc"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_daily_progress"
        self._attr_name = "Daily Schedule Progress"

    @property
    def native_value(self) -> Optional[int]:
        if self.coordinator.data and self.coordinator.data.status:
            return self.coordinator.data.status.raw_properties.get("schedule_progress")
        return None


class XiaomiFeederTargetPortionsSensor(XiaomiFeederBaseSensor):
    """Portions dispensed by the last feeding (SIID 2 / PIID 7, read-only)."""

    _attr_translation_key = "target_portions"
    _attr_icon = "mdi:numeric"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_target_portions"
        self._attr_name = "Last Feed Portions"

    @property
    def native_value(self) -> Optional[int]:
        if self.coordinator.data and self.coordinator.data.status:
            return self.coordinator.data.status.target_feeding_portions
        return None


class XiaomiFeederLastEatingSensor(XiaomiFeederBaseSensor):
    """Grams consumed in the most recent eating session based on bowl scale weight."""

    _attr_translation_key = "last_eating_session"
    _attr_native_unit_of_measurement = UnitOfMass.GRAMS
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:cat"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_last_eating_session"
        self._attr_name = "Last Eating Session"

    @property
    def native_value(self) -> Optional[int]:
        if self.coordinator.data and self.coordinator.data.last_eating_event:
            return self.coordinator.data.last_eating_event.get("eaten_grams")
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        if self.coordinator.data and self.coordinator.data.last_eating_event:
            return self.coordinator.data.last_eating_event
        return {}


class XiaomiFeederEatingHistorySensor(XiaomiFeederBaseSensor):
    """Eating history sensor containing a log of recent cat eating sessions from bowl scale data."""

    _attr_translation_key = "eating_history"
    _attr_icon = "mdi:history"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_eating_history"
        self._attr_name = "Eating History"

    @property
    def native_value(self) -> int:
        if self.coordinator.data:
            return len(self.coordinator.data.eating_history)
        return 0

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        if self.coordinator.data:
            return {"history": self.coordinator.data.eating_history}
        return {"history": []}


class XiaomiFeederDailyEatenCalculatedSensor(XiaomiFeederBaseSensor):
    """Daily cumulative eaten food weight calculated strictly from bowl scale weight deltas."""

    _attr_translation_key = "daily_eaten_calculated"
    _attr_native_unit_of_measurement = UnitOfMass.GRAMS
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_icon = "mdi:food-drumstick"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_daily_eaten_calculated"
        self._attr_name = "Daily Eaten (Calculated)"

    @property
    def native_value(self) -> int:
        if self.coordinator.data:
            return self.coordinator.data.daily_eaten_calculated
        return 0


