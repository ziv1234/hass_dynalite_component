"""Support for the Dynalite channels as switches."""
import asyncio
import logging

from homeassistant.core import callback

from .const import DOMAIN, LOGGER


def async_setup_channel_entry(category, hass, config_entry, async_add_entities):
    """Records the async_add_entities function to add them later when received from Dynalite."""
    LOGGER.debug("async_setup_entry " + category + " entry = %s", config_entry.data)
    bridge = hass.data[DOMAIN][config_entry.data["host"]]
    bridge.register_add_entities(category, async_add_entities)


class DynaliteBase:  # Deriving from Object so it doesn't override the entity (light, switch, cover, etc.)
    def __init__(self, device, bridge):
        self._listeners = []
        self._device = device
        self._bridge = bridge

    @property
    def name(self):
        """Return the name of the cover."""
        return self._device.name

    @property
    def unique_id(self):
        return self._device.unique_id

    @property
    def available(self):
        """Return if cover is available."""
        return self._device.available

    @property
    def hidden(self):
        """Return true if this switch should be hidden from UI."""
        return self._device.hidden

    @callback
    def set_hidden(self, hidden):
        return self._device.set_hidden(hidden)

    @callback
    async def async_update(self):
        return

    @property
    def device_info(self):
        return self._device.device_info

    @callback
    def try_schedule_ha(self):
        if (
            self.hass
        ):  # if it was not added yet to ha, need to update. will be updated when added to ha
            self.schedule_update_ha_state()
        else:
            LOGGER.debug("%s not ready - not updating" % self.name)

    async def async_added_to_hass(self):
        self.hass.async_create_task(self._bridge.entity_added_to_ha(self))

    @property
    def get_hass_area(self):
        return self._device.get_master_area

    @callback
    def add_listener(self, listener):
        self._listeners.append(listener)

    @callback
    def update_listeners(self):
        for listener in self._listeners:
            listener()
