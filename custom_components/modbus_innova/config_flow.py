"""Config flow for the Modbus Innova integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.modbus import get_hub
from homeassistant.components.modbus.const import (
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    DEFAULT_HUB,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME, CONF_SLAVE

from .const import CONF_HUB, DEFAULT_MAX_TEMP, DEFAULT_MIN_TEMP, DOMAIN


def _data_schema() -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_HUB, default=DEFAULT_HUB): str,
            vol.Required(CONF_SLAVE): vol.All(int, vol.Range(min=0, max=254)),
            vol.Optional(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.All(
                int, vol.Range(min=5, max=40)
            ),
            vol.Optional(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.All(
                int, vol.Range(min=5, max=40)
            ),
        }
    )


class ModbusInnovaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Modbus Innova."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                get_hub(self.hass, user_input[CONF_HUB])
            except KeyError:
                errors["base"] = "hub_not_found"
            else:
                self._async_abort_entries_match(
                    {CONF_HUB: user_input[CONF_HUB], CONF_SLAVE: user_input[CONF_SLAVE]}
                )
                await self.async_set_unique_id(f"{user_input[CONF_HUB]}_{user_input[CONF_SLAVE]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(_data_schema(), user_input),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            try:
                get_hub(self.hass, user_input[CONF_HUB])
            except KeyError:
                errors["base"] = "hub_not_found"
            else:
                if (
                    user_input[CONF_HUB] != reconfigure_entry.data[CONF_HUB]
                    or user_input[CONF_SLAVE] != reconfigure_entry.data[CONF_SLAVE]
                ):
                    self._async_abort_entries_match(
                        {CONF_HUB: user_input[CONF_HUB], CONF_SLAVE: user_input[CONF_SLAVE]}
                    )
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    title=user_input[CONF_NAME],
                    data=user_input,
                    unique_id=f"{user_input[CONF_HUB]}_{user_input[CONF_SLAVE]}",
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                _data_schema(), user_input or reconfigure_entry.data
            ),
            errors=errors,
        )
