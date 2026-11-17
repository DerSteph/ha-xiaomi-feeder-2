"""Tests for Xiaomi Feeder Sensor entities."""
from unittest.mock import MagicMock
import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.xiaomi_feeder.coordinator import FeederCoordinatorData
from custom_components.xiaomi_feeder.sensor import XiaomiFeederTargetPortionsSensor
from xiaomi_feeder_2.models import FeederStatus, SchedulePlan


@pytest.fixture
def mock_entry():
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_123"
    return entry


@pytest.fixture
def mock_coordinator(mock_entry):
    coord = MagicMock()
    coord.device_name = "Smart Feeder"
    return coord


def test_target_portions_sensor(mock_coordinator, mock_entry):
    """Test reading target portions telemetry value."""
    sensor = XiaomiFeederTargetPortionsSensor(mock_coordinator, mock_entry)

    status = MagicMock(spec=FeederStatus)
    status.target_feeding_portions = 2
    mock_coordinator.data = FeederCoordinatorData(
        status=status,
        schedule=SchedulePlan(enabled=True, meals=[], raw_string=""),
    )

    assert sensor.native_value == 2


def test_last_eating_sensor(mock_coordinator, mock_entry):
    """Test last eating session sensor reading."""
    from custom_components.xiaomi_feeder.sensor import XiaomiFeederLastEatingSensor

    sensor = XiaomiFeederLastEatingSensor(mock_coordinator, mock_entry)
    mock_coordinator.data = FeederCoordinatorData(
        status=MagicMock(spec=FeederStatus),
        schedule=SchedulePlan(enabled=True, meals=[], raw_string=""),
        last_eating_event={"eaten_grams": 14, "duration_seconds": 45, "time_str": "2026-08-17 10:30:00"},
    )
    assert sensor.native_value == 14
    assert sensor.extra_state_attributes["duration_seconds"] == 45


def test_eating_history_sensor(mock_coordinator, mock_entry):
    """Test eating history sensor count and attributes."""
    from custom_components.xiaomi_feeder.sensor import XiaomiFeederEatingHistorySensor

    sensor = XiaomiFeederEatingHistorySensor(mock_coordinator, mock_entry)
    events = [{"eaten_grams": 10}, {"eaten_grams": 15}]
    mock_coordinator.data = FeederCoordinatorData(
        status=MagicMock(spec=FeederStatus),
        schedule=SchedulePlan(enabled=True, meals=[], raw_string=""),
        eating_history=events,
    )
    assert sensor.native_value == 2
    assert sensor.extra_state_attributes["history"] == events


def test_daily_eaten_calculated_sensor(mock_coordinator, mock_entry):
    """Test calculated daily eaten sensor value."""
    from custom_components.xiaomi_feeder.sensor import XiaomiFeederDailyEatenCalculatedSensor

    sensor = XiaomiFeederDailyEatenCalculatedSensor(mock_coordinator, mock_entry)
    mock_coordinator.data = FeederCoordinatorData(
        status=MagicMock(spec=FeederStatus),
        schedule=SchedulePlan(enabled=True, meals=[], raw_string=""),
        daily_eaten_calculated=29,
    )
    assert sensor.native_value == 29


def test_cat_eating_binary_sensor(mock_coordinator, mock_entry):
    """Test cat eating binary sensor active state."""
    from custom_components.xiaomi_feeder.binary_sensor import XiaomiFeederCatEatingBinarySensor

    sensor = XiaomiFeederCatEatingBinarySensor(mock_coordinator, mock_entry)
    mock_coordinator.data = FeederCoordinatorData(
        status=MagicMock(spec=FeederStatus),
        schedule=SchedulePlan(enabled=True, meals=[], raw_string=""),
        is_cat_eating=True,
    )
    assert sensor.is_on is True

    mock_coordinator.data.is_cat_eating = False
    assert sensor.is_on is False

