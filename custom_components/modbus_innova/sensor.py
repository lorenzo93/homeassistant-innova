"""Platform for Fancoil Modbus water temperature sensor."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.modbus import get_hub
from homeassistant.components.modbus.const import (
    CALL_TYPE_REGISTER_HOLDING,
    DEFAULT_HUB,
)
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA as SENSOR_PLATFORM_SCHEMA,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_SLAVE,
    DEVICE_DEFAULT_NAME,
    UnitOfTemperature,
)

if TYPE_CHECKING:
    from homeassistant.components.modbus.modbus import ModbusHub
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

CONF_HUB = "hub"

PLATFORM_SCHEMA = SENSOR_PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_HUB, default=DEFAULT_HUB): cv.string,
        vol.Required(CONF_SLAVE): vol.All(int, vol.Range(min=0, max=254)),
        vol.Optional(CONF_NAME, default=DEVICE_DEFAULT_NAME): cv.string,
    }
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,  # noqa: ARG001
) -> None:
    """Set up the Modbus Innova water temperature sensor."""
    modbus_slave = config.get(CONF_SLAVE)
    name = config.get(CONF_NAME)
    hub = get_hub(hass, config[CONF_HUB])
    async_add_entities(
        [InnovaWaterTemperatureSensor(hub, modbus_slave, name)],
        update_before_add=True,
    )


class InnovaWaterTemperatureSensor(SensorEntity):
    """Representation of the fancoil water temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, hub: ModbusHub, modbus_slave: int | None, name: str | None) -> None:
        """Initialize the sensor."""
        self._hub = hub
        self._slave = modbus_slave
        self._attr_name = f"{name} Water Temperature"
        self._attr_unique_id = f"{name}_{modbus_slave}_water_temperature"

    async def async_update(self) -> None:
        """Update the sensor value."""
        result = await self._hub.async_pb_call(self._slave, 1, 1, CALL_TYPE_REGISTER_HOLDING)
        if result is None:
            _LOGGER.error("Error reading water temperature from fancoil")
            return

        self._attr_native_value = result.registers[0] / 10.0
