"""Tests for Xiaomi Feeder Skip Next Meal switch."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.xiaomi_feeder.coordinator import (
    FeederCoordinatorData,
    XiaomiFeederCoordinator,
)
from xiaomi_feeder_2.models import FeederStatus, ScheduleMeal, SchedulePlan


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.async_add_executor_job = AsyncMock()
    return hass


@pytest.fixture
def make_coordinator(mock_hass):
    def _make():
        with (
            patch("homeassistant.helpers.frame.report_usage"),
            patch("custom_components.xiaomi_feeder.coordinator.Store"),
            patch("custom_components.xiaomi_feeder.coordinator.XiaomiFeeder"),
        ):
            coordinator = XiaomiFeederCoordinator(
                mock_hass, "1.2.3.4", "token", "Smart Feeder", "test_entry_123"
            )
        coordinator.async_request_refresh = AsyncMock()
        coordinator._write_raw_hardware_schedule_sync = MagicMock()
        coordinator._store.async_save = AsyncMock()
        coordinator._store.async_load = AsyncMock(return_value=None)
        return coordinator

    return _make


@pytest.mark.asyncio
async def test_skip_next_meal_removes_next_meal(mock_hass, make_coordinator):
    """Skipping removes the next meal; the remaining meals are written comma-separated."""
    coordinator = make_coordinator()
    coordinator._stored_data = {"master_schedule_raw": "[1,03000101,15000101,23000101]"}

    status = MagicMock(spec=FeederStatus)
    meals = [
        ScheduleMeal(time="03:00", portions=1, repeat=1, raw="03000101"),
        ScheduleMeal(time="15:00", portions=1, repeat=1, raw="15000101"),
        ScheduleMeal(time="23:00", portions=1, repeat=1, raw="23000101"),
    ]
    next_feed_time = datetime(2026, 8, 16, 15, 0, tzinfo=timezone.utc)
    coordinator.data = FeederCoordinatorData(
        status=status,
        schedule=SchedulePlan(
            enabled=True,
            meals=meals,
            raw_string="[1,03000101,15000101,23000101]",
        ),
        next_feed_time=next_feed_time,
    )

    await coordinator.async_set_skip_next_meal(True)

    assert coordinator._skip_next_meal is True
    assert coordinator._skipped_meal_time == next_feed_time
    expected = "03000101,23000101"
    mock_hass.async_add_executor_job.assert_awaited_once_with(
        coordinator._write_raw_hardware_schedule_sync, expected
    )


@pytest.mark.asyncio
async def test_skip_next_meal_resume_restores_master_schedule(
    mock_hass, make_coordinator
):
    """Test resuming restores the master schedule to EEPROM."""
    coordinator = make_coordinator()
    coordinator._stored_data = {"master_schedule_raw": "[1,08000201,18300301]"}
    coordinator._skip_next_meal = True
    coordinator._skip_meals_count = 1
    coordinator._skipped_meal_time = datetime(2026, 8, 16, 8, 0, tzinfo=timezone.utc)

    await coordinator.async_set_skip_next_meal(False)

    assert coordinator._skip_next_meal is False
    assert coordinator._skip_meals_count == 0
    assert coordinator._skipped_meal_time is None
    mock_hass.async_add_executor_job.assert_awaited_once_with(
        coordinator._write_raw_hardware_schedule_sync, "[1,08000201,18300301]"
    )


@pytest.mark.asyncio
async def test_skip_next_meal_disable_today_method(mock_hass, make_coordinator):
    """With skip_method disable_today the meal stays in the list with status digits 00."""
    coordinator = make_coordinator()
    coordinator._stored_data = {
        "master_schedule_raw": "[1,03000101,15000101,23000101]",
        "skip_method": "disable_today",
    }
    meals = [
        ScheduleMeal(time="03:00", portions=1, repeat=1, raw="03000101"),
        ScheduleMeal(time="15:00", portions=1, repeat=1, raw="15000101"),
        ScheduleMeal(time="23:00", portions=1, repeat=1, raw="23000101"),
    ]
    coordinator.data = FeederCoordinatorData(
        status=MagicMock(spec=FeederStatus),
        schedule=SchedulePlan(enabled=True, meals=meals, raw_string="[1,03000101,15000101,23000101]"),
        next_feed_time=datetime(2026, 8, 16, 15, 0, tzinfo=timezone.utc),
    )

    await coordinator.async_set_skip_next_meal(True)

    mock_hass.async_add_executor_job.assert_awaited_once_with(
        coordinator._write_raw_hardware_schedule_sync, "03000101,15000100,23000101"
    )


@pytest.mark.asyncio
async def test_skip_method_setting(make_coordinator):
    """Default is remove; unknown or stale stored values fall back to it."""
    coordinator = make_coordinator()
    coordinator._stored_data = {}
    coordinator._async_save_storage = AsyncMock()
    assert coordinator.skip_method == "remove"

    await coordinator.async_set_skip_method("disable_today")
    assert coordinator.skip_method == "disable_today"
    coordinator._async_save_storage.assert_awaited_once()

    with pytest.raises(ValueError):
        await coordinator.async_set_skip_method("bogus")

    coordinator._stored_data["skip_method"] = "old_value"
    assert coordinator.skip_method == "remove"



def _two_meal_data(next_feed_time):
    meals = [
        ScheduleMeal(time="12:00", portions=1, repeat=127, raw="12000101"),
        ScheduleMeal(time="16:00", portions=1, repeat=127, raw="16000101"),
    ]
    return FeederCoordinatorData(
        status=MagicMock(spec=FeederStatus),
        schedule=SchedulePlan(enabled=True, meals=meals, raw_string="[1,12000101,16000101]"),
        next_feed_time=next_feed_time,
    )


@pytest.mark.asyncio
async def test_skip_state_is_persisted_and_cleared(make_coordinator):
    """An active skip is stored, and removed from storage again when resumed."""
    coordinator = make_coordinator()
    coordinator._stored_data = {"master_schedule_raw": "[1,12000101,16000101]"}
    meal = datetime(2026, 11, 18, 11, 0, tzinfo=timezone.utc)
    coordinator.data = _two_meal_data(meal)

    await coordinator.async_set_skip_next_meal(True)
    assert coordinator._stored_data["skip_state"] == {"meal_time": meal.isoformat(), "count": 1}
    coordinator._store.async_save.assert_awaited()

    await coordinator.async_set_skip_next_meal(False)
    assert "skip_state" not in coordinator._stored_data


@pytest.mark.asyncio
async def test_skip_state_survives_restart(make_coordinator):
    """A new coordinator (HA restart) loads the active skip from storage."""
    meal = datetime(2026, 11, 18, 11, 0, tzinfo=timezone.utc)
    coordinator = make_coordinator()
    coordinator._store.async_load = AsyncMock(return_value={
        "manual_portions": 1,
        "master_schedule_raw": "[1,12000101,16000101]",
        "skip_state": {"meal_time": meal.isoformat(), "count": 1},
    })

    await coordinator.async_load_storage()

    assert coordinator._skip_next_meal is True
    assert coordinator._skipped_meal_time == meal
    assert coordinator._skip_meals_count == 1


@pytest.mark.asyncio
async def test_broken_skip_state_is_dropped(make_coordinator):
    coordinator = make_coordinator()
    coordinator._store.async_load = AsyncMock(return_value={"skip_state": {"meal_time": "garbage"}})

    await coordinator.async_load_storage()

    assert coordinator._skip_next_meal is False
    assert "skip_state" not in coordinator._stored_data


def _run_executor_jobs(mock_hass):
    async def run(func, *args):
        return func(*args)

    mock_hass.async_add_executor_job = AsyncMock(side_effect=run)


def _idle_status():
    status = MagicMock(spec=FeederStatus)
    status.is_busy = False
    status.bowl_food_weight = 0
    status.target_feeding_portions = None
    status.daily_eaten_weight = 0
    return status


@pytest.mark.asyncio
async def test_update_restores_schedule_after_skipped_meal(mock_hass, make_coordinator):
    """After the skipped meal (e.g. right after a restart) the master schedule is written back."""
    _run_executor_jobs(mock_hass)
    coordinator = make_coordinator()
    coordinator._stored_data = {
        "master_schedule_raw": "[1,12000101,16000101]",
        "skip_state": {"meal_time": "2020-01-01T11:00:00+00:00", "count": 1},
    }
    coordinator._restore_skip_state()
    coordinator.client.status.return_value = _idle_status()
    coordinator.client.get_hardware_schedule.return_value = "[1,12000101,16000101]"

    await coordinator._async_update_data()

    coordinator._write_raw_hardware_schedule_sync.assert_called_once_with("[1,12000101,16000101]")
    assert coordinator._skip_next_meal is False
    assert "skip_state" not in coordinator._stored_data


@pytest.mark.asyncio
async def test_update_keeps_skip_when_restore_fails(mock_hass, make_coordinator):
    """If the feeder is unreachable, the skip stays stored and the restore is retried later."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    _run_executor_jobs(mock_hass)
    coordinator = make_coordinator()
    coordinator._stored_data = {
        "master_schedule_raw": "[1,12000101,16000101]",
        "skip_state": {"meal_time": "2020-01-01T11:00:00+00:00", "count": 1},
    }
    coordinator._restore_skip_state()
    coordinator.client.status.return_value = _idle_status()
    coordinator.client.get_hardware_schedule.return_value = "[1,16000101]"
    coordinator._write_raw_hardware_schedule_sync.side_effect = OSError("feeder offline")

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator._skip_next_meal is True
    assert "skip_state" in coordinator._stored_data
