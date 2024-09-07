"""Platform for Fancoil Modbus."""

from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.climate import (
    PLATFORM_SCHEMA as CLIMATE_PLATFORM_SCHEMA,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.modbus import (
    CALL_TYPE_REGISTER_HOLDING,
    DEFAULT_HUB,
    ModbusHub,
    get_hub,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_NAME,
    CONF_SLAVE,
    DEVICE_DEFAULT_NAME,
    UnitOfTemperature,
)
from homeassistant.components.modbus.const import CONF_MAX_TEMP, CONF_MIN_TEMP
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

CALL_TYPE_WRITE_REGISTER = "write_register"
CONF_HUB = "hub"

PLATFORM_SCHEMA = CLIMATE_PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_HUB, default=DEFAULT_HUB): cv.string,
        vol.Required(CONF_SLAVE): vol.All(int, vol.Range(min=0, max=254)),
        vol.Optional(CONF_NAME, default=DEVICE_DEFAULT_NAME): cv.string,
        vol.Optional(CONF_MIN_TEMP, default=5): vol.All(int, vol.Range(min=5, max=40)),
        vol.Optional(CONF_MAX_TEMP, default=40): vol.All(int, vol.Range(min=5, max=40)),
    }
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Flexit Platform."""
    modbus_slave = config.get(CONF_SLAVE)
    name = config.get(CONF_NAME)
    hub = get_hub(hass, config[CONF_HUB])
    async_add_entities([Fancoil(hub, modbus_slave, name, config)], True)


class Fancoil(ClimateEntity):
    """Representation of a fancoil AC unit."""

    _attr_fan_modes = ["Auto", "Silent", "Night", "High"]
    _attr_hvac_modes = [HVACMode.COOL, HVACMode.HEAT, HVACMode.OFF]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        hub: ModbusHub,
        modbus_slave: int | None,
        name: str | None,
        config: dict[str, Any],
    ) -> None:
        """Initialize the unit."""
        self._hub = hub
        self._attr_name = name
        self._slave = modbus_slave
        self._attr_fan_mode = None
        self._alarm = False
        self._water_temperature: int | None = None
        self._attr_actual_air_speed: int | None = None

        self._attr_min_temp = config[CONF_MIN_TEMP]
        self._attr_max_temp = config[CONF_MAX_TEMP]

    async def async_update(self) -> None:
        """Update unit attributes."""
        self._attr_target_temperature = await self._async_read_temp_from_register(
            CALL_TYPE_REGISTER_HOLDING, 231
        )
        self._attr_current_temperature = await self._async_read_temp_from_register(
            CALL_TYPE_REGISTER_HOLDING, 0
        )

        self._attr_actual_air_speed = await self._async_read_int16_from_register(
            CALL_TYPE_REGISTER_HOLDING, 15
        )

        self._water_temperature = await self._async_read_int16_from_register(
            CALL_TYPE_REGISTER_HOLDING, 1
        )

        prg = await self._async_read_int16_from_register(
            CALL_TYPE_REGISTER_HOLDING, 201
        )

        if (
            not Fancoil._is_set(prg, 0)
            and not Fancoil._is_set(prg, 1)
            and not Fancoil._is_set(prg, 2)
        ):
            self._attr_fan_mode = self._attr_fan_modes[0]
        elif (
            Fancoil._is_set(prg, 0)
            and not Fancoil._is_set(prg, 1)
            and not Fancoil._is_set(prg, 2)
        ):
            self._attr_fan_mode = self._attr_fan_modes[1]
        elif (
            not Fancoil._is_set(prg, 0)
            and Fancoil._is_set(prg, 1)
            and not Fancoil._is_set(prg, 2)
        ):
            self._attr_fan_mode = self._attr_fan_modes[2]
        elif (
            Fancoil._is_set(prg, 0)
            and Fancoil._is_set(prg, 1)
            and not Fancoil._is_set(prg, 2)
        ):
            self._attr_fan_mode = self._attr_fan_modes[3]
        else:
            _LOGGER.error("Received invalid PRG")
            return

        season = await self._async_read_int16_from_register(
            CALL_TYPE_REGISTER_HOLDING, 233
        )

        if season == 5:
            self._attr_hvac_mode = HVACMode.COOL
        elif season in (3, 0):
            self._attr_hvac_mode = HVACMode.HEAT
        else:
            _LOGGER.error("Received invalid season value: %s", season)
            return

        if Fancoil._is_set(prg, 7):
            self._attr_hvac_mode = HVACMode.OFF

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device specific state attributes."""
        return {
            "water_temperature": self._water_temperature,
            "fan_speed": self._attr_actual_air_speed,
        }

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new HVAC Mode."""
        curr_prg = await self._async_read_int16_from_register(
            CALL_TYPE_REGISTER_HOLDING, 201
        )
        if hvac_mode == HVACMode.OFF:
            await self._async_write_int16_to_register(201, (curr_prg | (1 << 7)))
            return
        if hvac_mode == HVACMode.COOL:
            season = 5
        elif hvac_mode == HVACMode.HEAT:
            season = 0
        else:
            _LOGGER.error("Modbus error setting hvac mode")
            return

        await self._async_write_int16_to_register(201, (curr_prg & ~(1 << 7)))
        await self._async_write_int16_to_register(233, season)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (target_temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            _LOGGER.error("Received invalid temperature")
            return

        if await self._async_write_int16_to_register(231, int(target_temperature * 10)):
            self._attr_target_temperature = target_temperature
        else:
            _LOGGER.error("Modbus error setting target temperature to Flexit")

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode."""
        index = self._attr_fan_modes.index(fan_mode)

        curr_prg = await self._async_read_int16_from_register(
            CALL_TYPE_REGISTER_HOLDING, 201
        )

        if index == 0:
            curr_prg = curr_prg & ~0b111
        elif index == 1:
            curr_prg = curr_prg & ~0b111 | 0b001
        elif index == 2:
            curr_prg = curr_prg & ~0b111 | 0b010
        else:
            curr_prg = curr_prg & ~0b111 | 0b011

        if self.fan_modes and await self._async_write_int16_to_register(201, curr_prg):
            self._attr_fan_mode = fan_mode
        else:
            _LOGGER.error("Modbus error setting fan mode")

    # Based on _async_read_register in ModbusThermostat class
    async def _async_read_int16_from_register(
        self, register_type: str, register: int
    ) -> int:
        """Read register using the Modbus hub slave."""
        result = await self._hub.async_pb_call(self._slave, register, 1, register_type)
        if result is None:
            _LOGGER.error("Error reading value from Flexit modbus adapter")
            return -1

        return int(result.registers[0])

    async def _async_read_temp_from_register(
        self, register_type: str, register: int
    ) -> float:
        result = float(
            await self._async_read_int16_from_register(register_type, register)
        )
        if not result:
            return -1
        return result / 10.0

    async def _async_write_int16_to_register(self, register: int, value: int) -> bool:
        return await self._hub.async_pb_call(
            self._slave, register, value, CALL_TYPE_WRITE_REGISTER
        )

    @staticmethod
    def _is_set(x: int, n: int) -> bool:
        return x & 1 << n != 0
