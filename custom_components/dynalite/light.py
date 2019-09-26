"""Support for the Philips Hue lights."""
import asyncio
import logging
from .const import DOMAIN, LOGGER
import pprint

from .dynalitebase import async_setup_channel_entry, DynaliteChannelBase

from homeassistant.components.light import SUPPORT_BRIGHTNESS, ATTR_BRIGHTNESS, Light
from homeassistant.core import callback

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Old way.

    """
    pass


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Records the async_add_entities function to add them later when received from Dynalite."""
    async_setup_channel_entry('light', hass, config_entry, async_add_entities)

class DynaliteChannelLight(DynaliteChannelBase, Light):
    """Representation of a Dynalite Channel as a Home Assistant Light."""

    def __init__(self, area, channel, name, type, hass_area, bridge, device):
        """Initialize the light."""
        self._area = area
        self._channel = channel
        self._name = name
        self._type = type
        self._hass_area = hass_area
        self._level = 0
        self._bridge = bridge
        self._device = device

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._level * 255

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._level > 0

    @callback
    def update_level(self, actual_level, target_level):
        self._level = actual_level
        
    async def async_turn_on(self, **kwargs):
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS] / 255.0
            self._device.turnOn(brightness=brightness)
        else:
            self._device.turnOn()

    async def async_turn_off(self, **kwargs):
        self._device.turnOff()

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS
