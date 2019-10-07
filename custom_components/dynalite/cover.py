"""Support for the Dynalite channels as covers."""
import asyncio
import logging
from .const import DOMAIN, LOGGER
import pprint

from homeassistant.const import CONF_COVERS
from homeassistant.components.cover import CoverDevice, ATTR_POSITION, ATTR_TILT_POSITION
from homeassistant.core import callback

from .dynalitebase import async_setup_channel_entry, DynaliteBase

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Old way.

    """
    pass


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Records the async_add_entities function to add them later when received from Dynalite."""
    async_setup_channel_entry('cover', hass, config_entry, async_add_entities)

class DynaliteCover(DynaliteBase, CoverDevice):
    """Representation of a Dynalite Channel as a Home Assistant Cover."""

    def __init__(self, device, bridge):
        """Initialize the cover."""
        super().__init__(device, bridge)

    @property
    def device_class(self):
        return self._device.device_class

    @property
    def current_cover_position(self):
        """return the position of the cover from 0 to 100"""
        return self._device.current_cover_position

    @property
    def is_opening(self):
        return self._device.is_opening
        
    @property
    def is_closing(self):
        return self._device.is_closing
        
    @property
    def is_closed(self):
        return self._device.is_closed

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        await self._device.async_open_cover(kwargs)
        
    async def async_close_cover(self, **kwargs):
        """Open the cover."""
        await self._device.async_close_cover(kwargs)

    async def async_set_cover_position(self, **kwargs):
        """Open the cover."""
        await self._device.async_set_cover_position(kwargs)
        
    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        await self._device.async_stop_cover(kwargs)

class DynaliteCoverWithTilt(DynaliteCover):
    """Representation of a Dynalite Channel as a Home Assistant Cover that uses up and down for tilt."""

    def __init__(self, device, bridge):
        """Initialize the cover."""
        super().__init__(device, bridge)

    @property
    def current_cover_tilt_position(self):
        return self._device.current_cover_tilt_position
    
    async def async_open_cover_tilt(self, **kwargs):
        await self._device.async_open_cover_tilt(kwargs)

    async def async_close_cover_tilt(self, **kwargs):
        await self._device.async_close_cover_tilt(kwargs)

    async def async_set_cover_tilt_position(self, **kwargs):
        await self._device.async_set_cover_tilt_position(kwargs)
    
    async def async_stop_cover_tilt(self, **kwargs):
        await self._device.async_stop_cover_tilt(kwargs)

