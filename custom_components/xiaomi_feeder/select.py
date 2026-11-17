"""Select platform for Xiaomi Smart Pet Feeder 2."""
from __future__ import annotations

from typing import Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEFAULT_MODEL,
    DOMAIN,
    FeederPIID,
    FeederSIID,
    INT_TO_SCREEN_MODE,
    SCREEN_DISPLAY_MAP,
    SKIP_METHODS,
)
from .coordinator import XiaomiFeederCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Xiaomi Feeder select entities."""
    coordinator: XiaomiFeederCoordinator = hass.data[DOMAIN][entry.entry_id]

    selects: list[SelectEntity] = [
        XiaomiFeederScreenDisplaySelect(coordinator, entry),
        XiaomiFeederSkipMethodSelect(coordinator, entry),
    ]

    async_add_entities(selects)


class XiaomiFeederBaseSelect(CoordinatorEntity[XiaomiFeederCoordinator], SelectEntity):
    """Base class for Xiaomi Feeder select entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        """Initialize base select."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=coordinator.device_name,
            manufacturer="Xiaomi",
            model=DEFAULT_MODEL,
        )


class XiaomiFeederScreenDisplaySelect(XiaomiFeederBaseSelect):
    """Screen metric mode select ('left', 'eaten', 'percentage')."""

    _attr_translation_key = "screen_display_mode"
    _attr_options = ["left", "eaten", "percentage"]
    _attr_icon = "mdi:television-guide"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_screen_display_mode"
        self._attr_name = "Screen Display Metric"

    @property
    def current_option(self) -> Optional[str]:
        if self.coordinator.data and self.coordinator.data.status:
            mode = self.coordinator.data.status.screen_display_mode
            if mode:
                mapped = SCREEN_DISPLAY_MAP.get(str(mode).lower())
                if mapped in self._attr_options:
                    return mapped
            # Check raw properties as fallback
            raw = self.coordinator.data.status.raw_properties.get(
                f"{FeederSIID.CUSTOM}_{FeederPIID.SCREEN_DISPLAY}"
            )
            if raw in INT_TO_SCREEN_MODE:
                return INT_TO_SCREEN_MODE[raw]
        return "left"

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_screen_display_mode(option)


class XiaomiFeederSkipMethodSelect(XiaomiFeederBaseSelect):
    """How "skip next meal" changes the schedule: remove the meal or disable it for today."""

    _attr_translation_key = "skip_method"
    _attr_options = SKIP_METHODS
    _attr_icon = "mdi:food-off-outline"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_skip_method"
        self._attr_name = "Skip Method"

    @property
    def current_option(self) -> Optional[str]:
        return self.coordinator.skip_method

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_skip_method(option)
        self.async_write_ha_state()
