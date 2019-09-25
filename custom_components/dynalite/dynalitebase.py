"""Support for the Dynalite channels as switches."""
import asyncio
import logging
from .const import DOMAIN, LOGGER, DATA_CONFIGS
import pprint

def async_setup_channel_entry(category, hass, config_entry, async_add_entities):
    """Records the async_add_entities function to add them later when received from Dynalite."""
    LOGGER.debug("async_setup_entry "+category+" entry = %s", pprint.pformat(config_entry.data))
    bridge = hass.data[DOMAIN][config_entry.data["host"]]
    bridge.async_add_entities[category] = async_add_entities

class DynaliteBase(object): # Deriving from Object so it doesn't override the entity (light, switch, cover, etc.)
    @property
    def name(self):
        """Return the name of the cover."""
        return self._name

    @property
    def available(self):
        """Return if cover is available."""
        return True
        
    @property
    def hidden(self):
        """Return true if this switch should be hidden from UI."""
        return getattr(self, '_hidden', False) # if not defined, assume false

    def set_hidden(self, hidden):
        setattr(self, '_hidden', True)
        
    async def async_update(self):
        return

    @property
    def device_info(self):
        return {
            'identifiers': {(DOMAIN, self.unique_id)},
            'name': self.name,
            'manufacturer': "Dynalite",
        }

    def try_schedule_ha(self):
        if self.hass: # if it was not added yet to ha, need to update. will be updated when added to ha
            self.schedule_update_ha_state()
        else:
            LOGGER.debug("%s not ready - not updating" % self._name)
            
    async def async_added_to_hass(self):
        self.hass.async_create_task(self._bridge.entity_added_to_ha(self))
        
    @property
    def get_hass_area(self):
        return self._hass_area

class DynaliteChannelBase(DynaliteBase): 
    """Representation of a Dynalite Channel as a Home Assistant Cover."""

    @property
    def unique_id(self):
        """Return the ID of this cover."""
        return "dynalite_area_"+str(self._area)+"_channel_"+str(self._channel)

