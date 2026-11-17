"""Tests for Xiaomi Feeder Coordinator schedule algorithms and models."""
from datetime import datetime, timedelta
import pytest
from unittest.mock import MagicMock

from xiaomi_feeder_2.models import FeederStatus, ScheduleMeal, SchedulePlan


def calculate_next_feeding_helper(meals: list[ScheduleMeal], now: datetime) -> tuple[datetime | None, int | None]:
    """Pure calculation logic testing next feeding time."""
    if not meals:
        return None, None

    candidates = []
    for meal in meals:
        try:
            hour, minute = map(int, meal.time.split(":"))
        except Exception:
            continue

        for day_offset in range(8):
            check_date = now.date() + timedelta(days=day_offset)
            check_weekday = check_date.weekday()
            repeat_mask = meal.repeat
            day_bit = 1 << check_weekday
            is_scheduled_for_day = (repeat_mask == 0 and day_offset == 0) or bool(repeat_mask & day_bit)

            if is_scheduled_for_day:
                candidate_dt = datetime(check_date.year, check_date.month, check_date.day, hour, minute, tzinfo=now.tzinfo)
                if candidate_dt > now:
                    candidates.append((candidate_dt, meal.portions))
                    break

    if not candidates:
        return None, None

    candidates.sort(key=lambda x: x[0])
    return candidates[0][0], candidates[0][1]


def test_schedule_plan_parsing():
    """Test SchedulePlan model parsing."""
    plan = SchedulePlan(
        enabled=True,
        meals=[
            ScheduleMeal(time="08:00", portions=2, repeat=127, raw="0800027f"),
            ScheduleMeal(time="18:30", portions=3, repeat=127, raw="121e037f"),
        ],
        raw_string="0800027f121e037f",
    )
    assert plan.enabled is True
    assert len(plan.meals) == 2
    assert plan.meals[0].portions == 2
    assert plan.meals[1].time == "18:30"
    assert plan.to_dict()["raw_string"] == "0800027f121e037f"


def test_calculate_next_feeding_future():
    """Test calculating upcoming meal when time is in the morning."""
    from datetime import timezone
    now = datetime(2026, 8, 16, 7, 0, 0, tzinfo=timezone.utc)
    meals = [
        ScheduleMeal(time="08:00", portions=2, repeat=127, raw="0800027f"),
        ScheduleMeal(time="18:30", portions=3, repeat=127, raw="121e037f"),
    ]
    next_dt, portions = calculate_next_feeding_helper(meals, now)
    assert next_dt is not None
    assert next_dt.hour == 8
    assert next_dt.minute == 0
    assert portions == 2


def test_calculate_next_feeding_after_morning_meal():
    """Test calculating upcoming meal when morning meal passed."""
    from datetime import timezone
    now = datetime(2026, 8, 16, 12, 0, 0, tzinfo=timezone.utc)
    meals = [
        ScheduleMeal(time="08:00", portions=2, repeat=127, raw="0800027f"),
        ScheduleMeal(time="18:30", portions=3, repeat=127, raw="121e037f"),
    ]
    next_dt, portions = calculate_next_feeding_helper(meals, now)
    assert next_dt is not None
    assert next_dt.hour == 18
    assert next_dt.minute == 30
    assert portions == 3


def test_calculate_next_feeding_next_day():
    """Test calculating upcoming meal wrapping around to tomorrow."""
    from datetime import timezone
    now = datetime(2026, 8, 16, 20, 0, 0, tzinfo=timezone.utc)
    meals = [
        ScheduleMeal(time="08:00", portions=2, repeat=127, raw="0800027f"),
    ]
    next_dt, portions = calculate_next_feeding_helper(meals, now)
    assert next_dt is not None
    assert next_dt.day == 17
    assert next_dt.hour == 8
    assert portions == 2


def test_eating_session_detection():
    """Test detecting a complete cat eating session purely from bowl scale weight deltas."""
    from custom_components.xiaomi_feeder.coordinator import XiaomiFeederCoordinator
    from custom_components.xiaomi_feeder.const import EVENT_EATING_COMPLETED
    from datetime import timezone

    mock_hass = MagicMock()
    mock_hass.bus = MagicMock()
    mock_hass.async_create_task = MagicMock()

    coord = XiaomiFeederCoordinator(
        hass=mock_hass,
        ip="192.168.1.100",
        token="12345678901234567890123456789012",
        name="Test Feeder",
        entry_id="entry_123",
        config_entry=MagicMock(),
    )
    coord._stored_data = {"eating_history": []}

    t0 = datetime(2026, 8, 17, 10, 0, 0, tzinfo=timezone.utc)
    # 1. Initial resting weight: 50g
    coord._process_bowl_weight(50, t0)
    assert coord._last_stable_bowl_weight == 50
    assert coord._is_cat_eating is False

    # 2. Cat comes and starts eating: scale drops to 40g
    t1 = datetime(2026, 8, 17, 10, 0, 5, tzinfo=timezone.utc)
    coord._process_bowl_weight(40, t1)
    assert coord._is_cat_eating is True
    assert coord._eating_session_start_weight == 50

    # 3. Cat resting paw on bowl during eating: scale fluctuates to 75g
    t2 = datetime(2026, 8, 17, 10, 0, 10, tzinfo=timezone.utc)
    coord._process_bowl_weight(75, t2)
    assert coord._is_cat_eating is True

    # 4. Cat finishes and leaves: weight drops to 35g
    t3 = datetime(2026, 8, 17, 10, 0, 15, tzinfo=timezone.utc)
    coord._process_bowl_weight(35, t3)
    assert coord._is_cat_eating is True  # 1st sample at 35g

    # 5. Weight stabilizes at 35g (2nd sample within ±1g)
    t4 = datetime(2026, 8, 17, 10, 0, 20, tzinfo=timezone.utc)
    coord._process_bowl_weight(35, t4)

    # Eating session completed!
    assert coord._is_cat_eating is False
    assert coord._last_stable_bowl_weight == 35

    history = coord._stored_data["eating_history"]
    assert len(history) == 1
    assert history[0]["eaten_grams"] == 15
    assert history[0]["duration_seconds"] == 15
    assert history[0]["bowl_weight_before"] == 50
    assert history[0]["bowl_weight_after"] == 35

    # HA event was fired
    mock_hass.bus.async_fire.assert_called_once_with(EVENT_EATING_COMPLETED, history[0])


def test_eating_session_noise_ignored():
    """Test that small scale jitter (< 2g) is not recorded as an eating session."""
    from custom_components.xiaomi_feeder.coordinator import XiaomiFeederCoordinator
    from datetime import timezone

    mock_hass = MagicMock()
    mock_hass.bus = MagicMock()

    coord = XiaomiFeederCoordinator(
        hass=mock_hass,
        ip="192.168.1.100",
        token="12345678901234567890123456789012",
        name="Test Feeder",
        entry_id="entry_123",
        config_entry=MagicMock(),
    )
    coord._stored_data = {"eating_history": []}

    t0 = datetime(2026, 8, 17, 10, 0, 0, tzinfo=timezone.utc)
    coord._process_bowl_weight(50, t0)

    # 1g drop (jitter)
    coord._process_bowl_weight(49, datetime(2026, 8, 17, 10, 0, 5, tzinfo=timezone.utc))
    coord._process_bowl_weight(49, datetime(2026, 8, 17, 10, 0, 10, tzinfo=timezone.utc))

    assert len(coord._stored_data["eating_history"]) == 0
    mock_hass.bus.async_fire.assert_not_called()


def test_dispensing_cooldown_ignores_weight_increase():
    """Test that motor dispensing food does not trigger false eating sessions."""
    from custom_components.xiaomi_feeder.coordinator import XiaomiFeederCoordinator
    from datetime import timezone

    mock_hass = MagicMock()
    mock_hass.bus = MagicMock()

    coord = XiaomiFeederCoordinator(
        hass=mock_hass,
        ip="192.168.1.100",
        token="12345678901234567890123456789012",
        name="Test Feeder",
        entry_id="entry_123",
        config_entry=MagicMock(),
    )
    coord._stored_data = {"eating_history": []}

    t0 = datetime(2026, 8, 17, 10, 0, 0, tzinfo=timezone.utc)
    coord._process_bowl_weight(10, t0)

    # Dispense starts
    coord._dispense_cooldown_until = datetime(2026, 8, 17, 10, 0, 20, tzinfo=timezone.utc)
    coord._process_bowl_weight(25, datetime(2026, 8, 17, 10, 0, 5, tzinfo=timezone.utc))

    assert coord._is_cat_eating is False
    assert coord._last_stable_bowl_weight == 25
    assert len(coord._stored_data["eating_history"]) == 0


def test_calculate_today_eaten():
    """Test summing grams eaten today from stored eating events."""
    from custom_components.xiaomi_feeder.coordinator import XiaomiFeederCoordinator
    from datetime import timezone

    mock_hass = MagicMock()

    coord = XiaomiFeederCoordinator(
        hass=mock_hass,
        ip="192.168.1.100",
        token="12345678901234567890123456789012",
        name="Test Feeder",
        entry_id="entry_123",
        config_entry=MagicMock(),
    )
    coord._stored_data = {
        "eating_history": [
            {"timestamp": "2026-08-16T15:00:00+00:00", "eaten_grams": 20}, # Yesterday
            {"timestamp": "2026-08-17T08:00:00+00:00", "eaten_grams": 12}, # Today
            {"timestamp": "2026-08-17T12:30:00+00:00", "eaten_grams": 15}, # Today
        ]
    }

    now = datetime(2026, 8, 17, 14, 0, 0, tzinfo=timezone.utc)
    today_eaten = coord._calculate_today_eaten(now)
    assert today_eaten == 27



def test_weight_poll_skips_while_device_busy():
    """The 5 s weight poll must not talk to the feeder while another call holds the lock."""
    import asyncio
    from unittest.mock import AsyncMock
    from custom_components.xiaomi_feeder.coordinator import XiaomiFeederCoordinator

    async def run():
        mock_hass = MagicMock()
        mock_hass.async_add_executor_job = AsyncMock(return_value=[{"value": 12}])
        coord = XiaomiFeederCoordinator(
            hass=mock_hass,
            ip="192.168.1.100",
            token="12345678901234567890123456789012",
            name="Test Feeder",
            entry_id="entry_123",
            config_entry=MagicMock(),
        )
        coord._stored_data = {"eating_history": []}

        async with coord._device_lock:
            await coord._async_poll_weight()
        mock_hass.async_add_executor_job.assert_not_called()

        await coord._async_poll_weight()
        mock_hass.async_add_executor_job.assert_called_once()
        assert not coord._device_lock.locked()

    asyncio.run(run())
