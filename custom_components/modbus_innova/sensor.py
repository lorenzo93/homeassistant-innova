"""Platform for Fancoil Modbus water temperature sensor."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.modbus import get_hub
from homeassistant.components.modbus.const import CALL_TYPE_REGISTER_HOLDING
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CONF_NAME, CONF_SLAVE, UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_HUB, DOMAIN

if TYPE_CHECKING:
    from homeassistant.components.modbus.modbus import ModbusHub
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Modbus Innova water temperature sensor from a config entry."""
    hub = get_hub(hass, entry.data[CONF_HUB])
    async_add_entities([InnovaWaterTemperatureSensor(hub, entry)], update_before_add=True)


class InnovaWaterTemperatureSensor(SensorEntity):
    """Representation of the fancoil water temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_translation_key = "water_temperature"

    def __init__(self, hub: ModbusHub, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        device_id = entry.unique_id or entry.entry_id
        self._hub = hub
        self._slave = entry.data[CONF_SLAVE]
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{device_id}_water_temperature"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=entry.data[CONF_NAME],
            manufacturer="Innova",
        )

    async def async_update(self) -> None:
        """Update the sensor value."""
        result = await self._hub.async_pb_call(self._slave, 1, 1, CALL_TYPE_REGISTER_HOLDING)
        if result is None:
            _LOGGER.error("Error reading water temperature from fancoil")
            return

        self._attr_native_value = result.registers[0] / 10.0
