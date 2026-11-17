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
