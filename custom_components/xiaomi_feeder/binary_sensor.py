"""Binary sensor platform for Xiaomi Smart Pet Feeder 2."""
from __future__ import annotations

from typing import Optional

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_MODEL, DOMAIN
from .coordinator import XiaomiFeederCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Xiaomi Feeder binary sensors."""
    coordinator: XiaomiFeederCoordinator = hass.data[DOMAIN][entry.entry_id]

    binary_sensors: list[BinarySensorEntity] = [
        XiaomiFeederHopperLowSensor(coordinator, entry),
        XiaomiFeederFoodStuckSensor(coordinator, entry),
        XiaomiFeederFoodOutErrorSensor(coordinator, entry),
        XiaomiFeederFoodHeapSensor(coordinator, entry),
        XiaomiFeederDeviceFaultSensor(coordinator, entry),
        XiaomiFeederDispensingSensor(coordinator, entry),
        XiaomiFeederRefillAlertSensor(coordinator, entry),
        XiaomiFeederDstActiveSensor(coordinator, entry),
        XiaomiFeederCatEatingBinarySensor(coordinator, entry),
    ]

    async_add_entities(binary_sensors)


class XiaomiFeederBaseBinarySensor(CoordinatorEntity[XiaomiFeederCoordinator], BinarySensorEntity):
    """Base class for Xiaomi Feeder binary sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=coordinator.device_name,
            manufacturer="Xiaomi",
            model=DEFAULT_MODEL,
        )


class XiaomiFeederHopperLowSensor(XiaomiFeederBaseBinarySensor):
    """Hopper food level low or empty alert."""

    _attr_translation_key = "hopper_low"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:tray-alert"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_hopper_low"
        self._attr_name = "Hopper Low"

    @property
    def is_on(self) -> Optional[bool]:
        if self.coordinator.data and self.coordinator.data.status:
            return self.coordinator.data.status.is_food_low
        return None


class XiaomiFeederFoodStuckSensor(XiaomiFeederBaseBinarySensor):
    """Motor jam / kibble stuck alert."""

    _attr_translation_key = "food_stuck"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert-octagon"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_food_stuck"
        self._attr_name = "Food Stuck / Motor Jam"

    @property
    def is_on(self) -> Optional[bool]:
        if self.coordinator.data and self.coordinator.data.status:
            return self.coordinator.data.status.food_stuck
        return None


class XiaomiFeederFoodOutErrorSensor(XiaomiFeederBaseBinarySensor):
    """Dispense error alert."""

    _attr_translation_key = "dispense_error"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert-circle"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_dispense_error"
        self._attr_name = "Dispense Error"

    @property
    def is_on(self) -> Optional[bool]:
        if self.coordinator.data and self.coordinator.data.status:
            return self.coordinator.data.status.food_out_error
        return None


class XiaomiFeederFoodHeapSensor(XiaomiFeederBaseBinarySensor):
    """Chute heap / kibble accumulation alert."""

    _attr_translation_key = "food_heap"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:tray-full"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_food_heap"
        self._attr_name = "Food Heap Detected"

    @property
    def is_on(self) -> Optional[bool]:
        if self.coordinator.data and self.coordinator.data.status:
            return self.coordinator.data.status.food_heap_detected
        return None


class XiaomiFeederDeviceFaultSensor(XiaomiFeederBaseBinarySensor):
    """General hardware fault."""

    _attr_translation_key = "fault"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:wrench-alert"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_fault"
        self._attr_name = "Device Fault"

    @property
    def is_on(self) -> Optional[bool]:
        if self.coordinator.data and self.coordinator.data.status:
            return self.coordinator.data.status.device_fault
        return None


class XiaomiFeederDispensingSensor(XiaomiFeederBaseBinarySensor):
    """Motor active dispensing busy status."""

    _attr_translation_key = "dispensing"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:cog-transfer-outline"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_dispensing"
        self._attr_name = "Dispensing"

    @property
    def is_on(self) -> Optional[bool]:
        if self.coordinator.data and self.coordinator.data.status:
            return self.coordinator.data.status.is_busy
        return None


class XiaomiFeederRefillAlertSensor(XiaomiFeederBaseBinarySensor):
    """Refill reminder timer alarm triggered."""

    _attr_translation_key = "refill_alert"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:bell-alert"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_refill_alert"
        self._attr_name = "Refill Alert"

    @property
    def is_on(self) -> Optional[bool]:
        if self.coordinator.data and self.coordinator.data.status:
            return bool(self.coordinator.data.status.raw_properties.get("add_meal_notify", 0))
        return None


class XiaomiFeederDstActiveSensor(XiaomiFeederBaseBinarySensor):
    """Device Daylight Saving Time (DST) active state."""

    _attr_translation_key = "dst_active"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:weather-sunny"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_dst_active"
        self._attr_name = "DST Active"

    @property
    def is_on(self) -> Optional[bool]:
        if self.coordinator.data and self.coordinator.data.status:
            return self.coordinator.data.status.dst_active
        return None


class XiaomiFeederCatEatingBinarySensor(XiaomiFeederBaseBinarySensor):
    """Binary sensor indicating if a cat is currently at the bowl eating."""

    _attr_translation_key = "cat_eating"
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY
    _attr_icon = "mdi:cat"

    def __init__(self, coordinator: XiaomiFeederCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_cat_eating"
        self._attr_name = "Cat Eating"

    @property
    def is_on(self) -> bool:
        if self.coordinator.data:
            return bool(self.coordinator.data.is_cat_eating)
        return False

