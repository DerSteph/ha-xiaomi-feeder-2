"""Integration for Xiaomi Smart Pet Feeder 2."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_IP,
    CONF_NAME,
    CONF_TOKEN,
    DEFAULT_NAME,
    DOMAIN,
)
from .coordinator import XiaomiFeederCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.TEXT,
]

# Service Schemas
SERVICE_FEED = "feed"
SERVICE_FEED_SCHEMA = vol.Schema(
    {
        vol.Optional("portions", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
    }
)

SERVICE_CALIBRATE_SCALE = "calibrate_scale"
SERVICE_CALIBRATE_SCHEMA = vol.Schema({})

SERVICE_SKIP_NEXT_MEAL = "skip_next_meal"
SERVICE_SKIP_NEXT_MEAL_SCHEMA = vol.Schema(
    {
        vol.Optional("count", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=10)),
        vol.Optional("enabled", default=True): cv.boolean,
    }
)

SERVICE_SET_REFILL_REMINDER = "set_refill_reminder"
SERVICE_SET_REFILL_REMINDER_SCHEMA = vol.Schema(
    {
        vol.Required("enabled"): cv.boolean,
        vol.Optional("interval_hours", default=6): vol.All(vol.Coerce(int), vol.Range(min=1, max=24)),
    }
)

SERVICE_SET_INTAKE_ALARM = "set_intake_alarm"
SERVICE_SET_INTAKE_ALARM_SCHEMA = vol.Schema(
    {
        vol.Required("enabled"): cv.boolean,
        vol.Optional("threshold_pct", default=10): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
    }
)

SERVICE_CLEAR_REFILL_ALERT = "clear_refill_alert"
SERVICE_CLEAR_REFILL_ALERT_SCHEMA = vol.Schema({})

SERVICE_CLEAR_INTAKE_ALERT = "clear_intake_alert"
SERVICE_CLEAR_INTAKE_ALERT_SCHEMA = vol.Schema({})

SERVICE_CLEAR_SCHEDULE = "clear_schedule"
SERVICE_CLEAR_SCHEDULE_SCHEMA = vol.Schema({})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Xiaomi Pet Feeder from a config entry."""
    ip = entry.data[CONF_IP]
    token = entry.data[CONF_TOKEN]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)

    coordinator = XiaomiFeederCoordinator(
        hass=hass,
        ip=ip,
        token=token,
        name=name,
        entry_id=entry.entry_id,
        config_entry=entry,
    )

    await coordinator.async_load_storage()
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register custom services
    async def async_handle_feed(call: ServiceCall) -> None:
        portions = call.data.get("portions", 1)
        await coordinator.async_feed(portions)

    async def async_handle_calibrate(call: ServiceCall) -> None:
        await coordinator.async_calibrate_scale()

    async def async_handle_skip_next_meal(call: ServiceCall) -> None:
        count = call.data.get("count", 1)
        enabled = call.data.get("enabled", True)
        await coordinator.async_set_skip_next_meal(skip=enabled, count=count)

    async def async_handle_set_refill(call: ServiceCall) -> None:
        enabled = call.data["enabled"]
        hours = call.data.get("interval_hours", 6)
        await coordinator.async_set_refill_reminder(enabled, hours)

    async def async_handle_set_intake(call: ServiceCall) -> None:
        enabled = call.data["enabled"]
        threshold = call.data.get("threshold_pct", 10)
        await coordinator.async_set_intake_alarm(enabled, threshold)

    async def async_handle_clear_refill(call: ServiceCall) -> None:
        await coordinator.async_clear_refill_alert()

    async def async_handle_clear_intake(call: ServiceCall) -> None:
        await coordinator.async_clear_intake_alert()

    async def async_handle_clear_schedule(call: ServiceCall) -> None:
        await coordinator.async_clear_hardware_schedule()

    # Service bindings
    services = [
        (SERVICE_FEED, async_handle_feed, SERVICE_FEED_SCHEMA),
        (SERVICE_CALIBRATE_SCALE, async_handle_calibrate, SERVICE_CALIBRATE_SCHEMA),
        (SERVICE_SKIP_NEXT_MEAL, async_handle_skip_next_meal, SERVICE_SKIP_NEXT_MEAL_SCHEMA),
        (SERVICE_SET_REFILL_REMINDER, async_handle_set_refill, SERVICE_SET_REFILL_REMINDER_SCHEMA),
        (SERVICE_SET_INTAKE_ALARM, async_handle_set_intake, SERVICE_SET_INTAKE_ALARM_SCHEMA),
        (SERVICE_CLEAR_REFILL_ALERT, async_handle_clear_refill, SERVICE_CLEAR_REFILL_ALERT_SCHEMA),
        (SERVICE_CLEAR_INTAKE_ALERT, async_handle_clear_intake, SERVICE_CLEAR_INTAKE_ALERT_SCHEMA),
        (SERVICE_CLEAR_SCHEDULE, async_handle_clear_schedule, SERVICE_CLEAR_SCHEDULE_SCHEMA),
    ]

    for service_name, handler, schema in services:
        if not hass.services.has_service(DOMAIN, service_name):
            hass.services.async_register(DOMAIN, service_name, handler, schema=schema)

    coordinator.async_start_weight_polling()

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: XiaomiFeederCoordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        coordinator.async_stop_weight_polling()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

