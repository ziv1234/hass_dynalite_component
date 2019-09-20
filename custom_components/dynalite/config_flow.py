"""Config flow to configure Philips Hue."""
import asyncio
import json
import os

import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN, LOGGER

import pprint # XXX Remove or put in the right place

@callback
def configured_hosts(hass):
    """Return a set of the configured hosts."""
    return set(
        entry.data["host"] for entry in hass.config_entries.async_entries(DOMAIN)
    )

class DynaliteFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Dynalite config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize the Dynalite flow."""
        self.host = None

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        return await self.async_step_init(user_input)

    async def async_step_init(self, user_input=None):
        """Handle a flow start."""
        LOGGER.error("async_step_init - not sure when this happens") # XXX
        if user_input is not None:
            self.host = self.context["host"] = user_input["host"]
            return await self._entry_from_bridge(host)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required("host"): vol.In(hosts)}),
        )

    async def async_step_import(self, import_info):
        """Import a new bridge as a config entry.

        """
        LOGGER.debug("async_step_import - %s" % pprint.pformat(import_info))
        host = self.context["host"] = import_info["host"]
        return await self._entry_from_bridge(host)

    async def _entry_from_bridge(self, host):
        """Return a config entry from an initialized bridge."""
        LOGGER.debug("entry_from_bridge - %s" % pprint.pformat(host))
        # Remove all other entries of hubs with same ID or host
        
        same_hub_entries = [
            entry.entry_id
            for entry in self.hass.config_entries.async_entries(DOMAIN)
            if entry.data["host"] == host
        ]

        LOGGER.debug("entry_from_bridge same_hub - %s" % pprint.pformat(same_hub_entries))

        if same_hub_entries:
            await asyncio.wait(
                [
                    self.hass.config_entries.async_remove(entry_id)
                    for entry_id in same_hub_entries
                ]
            )

        return self.async_create_entry(
            title=host,
            data={"host": host},
        )
