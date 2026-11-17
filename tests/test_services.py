"""Tests for resolving which feeder(s) an action call targets."""
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.xiaomi_feeder import _target_coordinators
from custom_components.xiaomi_feeder.const import DOMAIN


def _hass(*entry_ids: str) -> MagicMock:
    hass = MagicMock()
    hass.data = {DOMAIN: {entry_id: MagicMock(name=entry_id) for entry_id in entry_ids}}
    return hass


def _call(**data) -> MagicMock:
    call = MagicMock()
    call.data = data
    return call


def _registry(devices: dict[str, list[str]]) -> MagicMock:
    registry = MagicMock()
    registry.async_get.side_effect = lambda device_id: (
        MagicMock(config_entries=set(devices[device_id])) if device_id in devices else None
    )
    return registry


def test_single_feeder_without_device_id():
    hass = _hass("left")
    assert _target_coordinators(hass, _call()) == [hass.data[DOMAIN]["left"]]


def test_several_feeders_require_device_id():
    hass = _hass("left", "right")
    with pytest.raises(ServiceValidationError):
        _target_coordinators(hass, _call())


def test_device_id_selects_the_right_feeder():
    hass = _hass("left", "right")
    registry = _registry({"dev_left": ["left"], "dev_right": ["right"]})
    with patch("custom_components.xiaomi_feeder.dr.async_get", return_value=registry):
        assert _target_coordinators(hass, _call(device_id=["dev_right"])) == [hass.data[DOMAIN]["right"]]
        assert _target_coordinators(hass, _call(device_id=["dev_left", "dev_right"])) == [
            hass.data[DOMAIN]["left"],
            hass.data[DOMAIN]["right"],
        ]


def test_unknown_or_foreign_device_is_rejected():
    hass = _hass("left", "right")
    registry = _registry({"dev_lamp": ["some_other_entry"]})
    with patch("custom_components.xiaomi_feeder.dr.async_get", return_value=registry):
        with pytest.raises(ServiceValidationError):
            _target_coordinators(hass, _call(device_id=["dev_lamp"]))
        with pytest.raises(ServiceValidationError):
            _target_coordinators(hass, _call(device_id=["missing"]))
