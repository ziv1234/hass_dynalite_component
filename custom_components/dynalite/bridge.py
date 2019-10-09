"""Code to handle a Dynalite bridge."""
import asyncio
import pprint
import copy

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr, area_registry as ar, discovery

from .const import (
    CONF_CHANNEL, CONF_AREA, CONF_PRESET, CONF_FACTOR, CONF_CHANNELTYPE, CONF_HIDDENENTITY, CONF_TILTPERCENTAGE,
    CONF_AREAOVERRIDE, CONF_CHANNELCLASS, CONF_TEMPLATE, CONF_ROOM_ON, CONF_ROOM_OFF, DEFAULT_TEMPLATES, CONF_ROOM, 
    DEFAULT_CHANNELTYPE, CONF_TEMPLATEOVERRIDE, DEFAULT_COVERCHANNELCLASS, DEFAULT_COVERFACTOR, CONF_TRIGGER,
    CONF_CHANNELCOVER, CONF_NODEFAULT, DOMAIN, DATA_CONFIGS, LOGGER, CONF_BRIDGES, CONF_AREACREATE, CONF_HOST,
    CONF_AREA_CREATE_MANUAL, CONF_AREA_CREATE_ASSIGN, CONF_AREA_CREATE_AUTO, ENTITY_CATEGORIES, CONF_COVERS, CONF_NAME, 
    CONF_ALL
)

from dynalite_devices_lib.dynalite_devices import DynaliteDevices

from .light import DynaliteLight
from .switch import DynaliteSwitch
from .cover import DynaliteCover, DynaliteCoverWithTilt

class BridgeError(Exception):
    def __init__(self, message):
        self.message = message

class DynaliteBridge:
    """Manages a single Dynalite bridge."""

    def __init__(self, hass, config_entry):
        """Initialize the system."""
        self.config_entry = config_entry
        self.hass = hass
        self.area = {}
        self.async_add_entities = {}
        self.waiting_entities = {}
        self.all_entities = {}
        self.area_reg = None
        self.device_reg = None

    @property
    def host(self):
        """Return the host of this bridge."""
        return self.config_entry.data[CONF_HOST]

    async def async_setup(self, tries=0):
        """Set up a Dynalite bridge based on host parameter."""
        host = self.host
        hass = self.hass
        self.area_reg = await ar.async_get_registry(hass)
        self.device_reg = await dr.async_get_registry(hass)
        LOGGER.debug("component bridge async_setup - %s" % pprint.pformat(self.config_entry.data))
        self.hass.loop.set_debug(True) # XXX
        if (host not in hass.data[DOMAIN][DATA_CONFIGS]):
            LOGGER.info("invalid host - %s" % host)
            return False
        
        self.config = hass.data[DOMAIN][DATA_CONFIGS][host]

        # Configure the dynalite devices
        self._dynalite_devices = DynaliteDevices(config=self.config, loop=hass.loop, newDeviceFunc=self.addDevices, updateDeviceFunc=self.updateDevice)
        await self._dynalite_devices.async_setup()
        
        for category in ENTITY_CATEGORIES:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(self.config_entry, category) # XXX maybe handle the race condition if need to use before init. not urgent
            )

        LOGGER.debug("XXX finished dynalite async_setup")
        return True

    @callback
    def addDevices(self, devices):
        LOGGER.debug("XXX addDevices %s", devices)
        added_entities = {}
        for category in ENTITY_CATEGORIES:
            added_entities[category] = []

        for device in devices:
            category = device.category
            if category == 'light':
                entity = DynaliteLight(device, self)
            elif category == 'switch':
                entity = DynaliteSwitch(device, self)
            elif category == 'cover':
                try:
                    temp = device.current_cover_tilt_position # will throw AttributeError if not implemented in class
                    LOGGER.debug("XXX with tilt device=%s", device)
                    entity = DynaliteCoverWithTilt(device, self)
                except AttributeError:
                    LOGGER.debug("XXX without tilt device=%s", device)
                    entity = DynaliteCover(device, self)
            else:
                LOGGER.warning("Illegal device category %s", category)
                continue
            added_entities[category].append(entity)
            self.all_entities[entity.unique_id] = entity
            
        for category in ENTITY_CATEGORIES:
            if added_entities[category]:
                self.add_entities_when_registered(category, added_entities[category])
    
    @callback
    def updateDevice(self, device):
        if device == CONF_ALL:
            for uid in self.all_entities:
                self.all_entities[uid].try_schedule_ha()
        else:
            uid = device.unique_id
            if uid in self.all_entities:
                self.all_entities[uid].try_schedule_ha()
    
    @callback
    def register_add_entities(self, category, async_add_entities):
        LOGGER.debug("XXX register_add_entities %s", category)
        self.async_add_entities[category] = async_add_entities
        if category in self.waiting_entities:
            self.async_add_entities[category](self.waiting_entities[category])

    def add_entities_when_registered(self, category, entities):
        if not entities:
            return
        if category in self.async_add_entities:
            self.async_add_entities[category](entities)
        else: # handle it later when it is registered
            if category not in self.waiting_entities:
                self.waiting_entities[category] = []
            self.waiting_entities[category].extend(entities)

    async def async_reset(self):
        """Reset this bridge to default state.

        Will cancel any scheduled setup retry and will unload
        the config entry.
        """
        # XXX don't think it is working - not sure how to test it:
        # so throwing an exception
        raise BridgeError("Dynalite async_reset called. not sure it is well implemented")
        results = await asyncio.gather(
            self.hass.config_entries.async_forward_entry_unload(
                self.config_entry, "light"
            ),
        )
        # None and True are OK
        return False not in results

    async def entity_added_to_ha(self, entity):
        areacreate = self.config[CONF_AREACREATE].lower()
        if areacreate == CONF_AREA_CREATE_MANUAL:
            LOGGER.debug("area assignment set to manual - ignoring")
            return # only need to update the areas if it is 'assign' or 'create'
        if areacreate not in [CONF_AREA_CREATE_ASSIGN, CONF_AREA_CREATE_AUTO]:
            LOGGER.debug(CONF_AREACREATE + " has unknown value of %s - assuming \"" + CONF_AREA_CREATE_MANUAL + "\" and ignoring", areacreate)
            return
        uniqueID = entity.unique_id
        hassArea = entity.get_hass_area
        if hassArea != "":
            LOGGER.debug("assigning hass area %s to entity %s" % (hassArea, uniqueID))
            device = self.device_reg.async_get_device({("dynalite-devices", uniqueID)}, ()) # XXX
            if not device:
                LOGGER.error("uniqueID %s has no device ID", uniqueID)
                return
            areaEntry = self.area_reg._async_is_registered(hassArea)
            if not areaEntry:
                if areacreate != CONF_AREA_CREATE_AUTO:
                    LOGGER.debug("Area %s not registered and " + CONF_AREACREATE + " is not \"" + CONF_AREA_CREATE_AUTO + "\" - ignoring", hassArea)
                    return
                else:
                    LOGGER.debug("Creating new area %s", hassArea)
                    areaEntry = self.area_reg.async_create(hassArea)
            LOGGER.debug("assigning deviceid=%s area_id=%s" % (device.id, areaEntry.id))
            self.device_reg.async_update_device(device.id, area_id=areaEntry.id)
