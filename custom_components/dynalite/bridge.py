"""Code to handle a Hue bridge."""
import asyncio

from homeassistant import config_entries
from homeassistant.const import CONF_COVERS, CONF_NAME
from homeassistant.helpers import device_registry as dr, area_registry as ar
import pprint

from .const import (DOMAIN, LOGGER, CONF_BRIDGES, DATA_CONFIGS, CONF_CHANNEL, CONF_AREA, CONF_PRESET, CONF_FACTOR, CONF_CHANNELTYPE, CONF_HIDDENCHANNEL, CONF_TILTPERCENTAGE,
                    CONF_AREACREATE, CONF_AREAOVERRIDE)
from .dynalite_lib.dynalite import Dynalite
from .light import DynaliteChannelLight
from .switch import DynaliteChannelSwitch, DynalitePresetSwitch
from .cover import DynaliteChannelCover, DynaliteChannelCoverWithTilt


class DynaliteBridge:
    """Manages a single Dynalite bridge."""

    def __init__(self, hass, config_entry):
        """Initialize the system."""
        self.config_entry = config_entry
        self.hass = hass
        self.area = {}
        self.async_add_entities = {}
        self.added_channels = {}
        self.added_presets = {}
        self.area_reg = None
        self.device_reg = None
        self.config = None

    @property
    def host(self):
        """Return the host of this bridge."""
        return self.config_entry.data["host"]

    async def async_setup(self, tries=0):
        """Set up a Dynalite bridge based on host parameter."""
        host = self.host
        hass = self.hass
        self.area_reg = await ar.async_get_registry(hass)
        self.device_reg = await dr.async_get_registry(hass)
        LOGGER.debug("bridge async_setup - %s" % pprint.pformat(self.config_entry.data))
        
        if (host not in hass.data[DATA_CONFIGS]):
            LOGGER.info("invalid host - %s" % host)
            return False
        
        self.config = hass.data[DATA_CONFIGS][host]
        self._dynalite = Dynalite(config=self.config, loop=hass.loop)
        eventHandler = self._dynalite.addListener(  # XXX Maybe remove
            listenerFunction=self.handleEvent)
        eventHandler.monitorEvent('*') # XXX Maybe remove
        newPresetHandler = self._dynalite.addListener(
            listenerFunction=self.handleNewPreset)
        newPresetHandler.monitorEvent('NEWPRESET')
        presetChangeHandler = self._dynalite.addListener(
            listenerFunction=self.handlePresetChange)
        presetChangeHandler.monitorEvent('PRESET')
        newChannelHandler = self._dynalite.addListener(
            listenerFunction=self.handleNewChannel)
        newChannelHandler.monitorEvent('NEWCHANNEL')
        channelChangeHandler = self._dynalite.addListener(
            listenerFunction=self.handleChannelChange)
        channelChangeHandler.monitorEvent('CHANNEL')
        # Start Dynalite
        self._dynalite.start()
        self._state = 'Connected'
        for category in ['light', 'switch', 'cover']:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(self.config_entry, category) # XXX maybe handle the race condition if need to use before init. not urgent
            )

        return True

    async def async_reset(self):
        """Reset this bridge to default state.

        Will cancel any scheduled setup retry and will unload
        the config entry.
        """
        # XXX don't think it is working - not sure how to test it:
        # so throwing an exception
        aaa = bbb
        results = await asyncio.gather(
            self.hass.config_entries.async_forward_entry_unload(
                self.config_entry, "light"
            ),
        )
        # None and True are OK
        return False not in results

    def handleEvent(self, event=None, dynalite=None):
        LOGGER.debug("handleEvent - type=%s event=%s" % (event.eventType, pprint.pformat(event.data)))
        return

    def getHassArea(self, area):
        areaConfig=self.config['area'][str(area)] if str(area) in self.config['area'] else None
        hassArea = areaConfig[CONF_NAME]
        if CONF_AREAOVERRIDE in areaConfig:
            overrideArea = areaConfig[CONF_AREAOVERRIDE]
            hassArea = overrideArea if overrideArea.lower() != 'none' else ''
        return hassArea
        
    def handleNewPreset(self, event=None, dynalite=None):
        LOGGER.debug("handleNewPreset - event=%s" % pprint.pformat(event.data))
        if not hasattr(event, 'data'):
            return
        if not 'area' in event.data:
            return
        curArea = event.data['area']
        if not 'preset' in event.data:
            return
        curPreset = event.data['preset']
        if not 'name' in event.data:
            return
        curName = event.data['name']
        curDevice = self._dynalite.devices['area'][curArea].preset[curPreset]
        hassArea = self.getHassArea(curArea)
        newSwitch = DynalitePresetSwitch(curArea, curPreset, curName, "preset", hassArea, self, curDevice)
        self.async_add_entities['switch']([newSwitch])
        if (curArea not in self.added_presets):
            self.added_presets[curArea] = {}
        self.added_presets[curArea][curPreset] = newSwitch
        LOGGER.debug("Creating Dynalite preset area=%s preset=%s name=%s" % (curArea, curPreset, curName))

    def handlePresetChange(self, event=None, dynalite=None):
        LOGGER.debug("handlePresetChange - event=%s" % pprint.pformat(event.data))
        if not hasattr(event, 'data'):
            return
        if not 'area' in event.data:
            return
        curArea = event.data['area']
        if not 'preset' in event.data:
            return
        curPreset = event.data['preset']
        if int(curArea) in self.added_presets:
            for curPresetInArea in self.added_presets[int(curArea)]:
                self.added_presets[int(curArea)][curPresetInArea].try_schedule_ha()

    def handleNewChannel(self, event=None, dynalite=None):
        LOGGER.debug("handleNewChannel - event=%s" % pprint.pformat(event.data))
        if not hasattr(event, 'data'):
            return
        if not 'area' in event.data:
            return
        curArea = event.data['area']
        if not 'channel' in event.data:
            return
        curChannel = event.data['channel']
        if not 'name' in event.data:
            return
        curName = event.data['name']
        curDevice = self._dynalite.devices['area'][curArea].channel[curChannel]
        channelConfig=self.config['area'][str(curArea)]['channel'][str(curChannel)] if str(curChannel) in self.config['area'][str(curArea)]['channel'] else None
        LOGGER.debug("handleNewChannel - channelConfig=%s" % pprint.pformat(channelConfig))
        channelType = channelConfig[CONF_CHANNELTYPE] if channelConfig and CONF_CHANNELTYPE in channelConfig else 'light'
        channelType = channelType.lower()
        hassArea = self.getHassArea(curArea)
        if channelType == 'light':
            newEntity = DynaliteChannelLight(curArea, curChannel, curName, channelType, hassArea, self, curDevice)
            self.async_add_entities['light']([newEntity])
        elif channelType == 'switch':
            newEntity = DynaliteChannelSwitch(curArea, curChannel, curName, channelType, hassArea, self, curDevice)
            self.async_add_entities['switch']([newEntity])
        elif channelType == 'cover':
            factor = channelConfig[CONF_FACTOR]
            if CONF_TILTPERCENTAGE in channelConfig:
                newEntity = DynaliteChannelCoverWithTilt(curArea, curChannel, curName, channelType, factor, channelConfig[CONF_TILTPERCENTAGE], hassArea, self, curDevice)
            else:
                newEntity = DynaliteChannelCover(curArea, curChannel, curName, channelType, factor, hassArea, self, curDevice)
            self.async_add_entities['cover']([newEntity])
        else:
            LOGGER.info("unknown chnanel type %s - ignoring", channelType)
            return
        if (curArea not in self.added_channels):
            self.added_channels[curArea] = {}
        self.added_channels[curArea][curChannel] = newEntity
        if channelConfig[CONF_HIDDENCHANNEL]:
            newEntity.set_hidden(True)   
        LOGGER.debug("Creating Dynalite channel area=%s channel=%s name=%s" % (curArea, curChannel, curName))

    def handleChannelChange(self, event=None, dynalite=None):
        LOGGER.debug("handleChannelChange - event=%s" % pprint.pformat(event.data))
        LOGGER.debug("handleChannelChange called event = %s" % event.msg)
        if not hasattr(event, 'data'):
            return
        if not 'area' in event.data:
            return
        curArea = event.data['area']
        if not 'channel' in event.data:
            return
        curChannel = event.data['channel']
        if not 'target_level' in event.data:
            return
        action = event.data['action']
        if action == 'report':
            actual_level = (255 - event.data['actual_level']) / 254
            target_level = (255 - event.data['target_level']) / 254
            if (int(curArea) in self.added_channels) and (int(curChannel) in self.added_channels[int(curArea)]):
                channelToSet = self.added_channels[int(curArea)][int(curChannel)]
                channelToSet.update_level(actual_level, target_level)
                channelToSet.try_schedule_ha() # to only call if it was already added to ha
        elif action == 'cmd':
            if (int(curArea) in self.added_channels) and (int(curChannel) in self.added_channels[int(curArea)]):
                self.added_channels[int(curArea)][int(curChannel)].try_schedule_ha()
        else:
            LOGGER.error("unknown action for channel change %s", action)
        
    async def entity_added_to_ha(self, entity):
        areacreate = self.config[CONF_AREACREATE].lower()
        if areacreate == 'manual':
            LOGGER.debug("area assignment set to manual - ignoring")
            return # only need to update the areas if it is 'assign' or 'create'
        if areacreate not in ['assign', 'create']:
            LOGGER.debug(CONF_AREACREATE + " has unknown value of %s - assuming \"manual\" and ignoring", areacreate) # XXX think about how to do it in vol/cv
            return
        uniqueID = entity.unique_id
        hassArea = entity.get_hass_area
        if hassArea != "":
            LOGGER.debug("assigning hass area %s to entity %s" % (hassArea, uniqueID))
            device = self.device_reg.async_get_device({(DOMAIN, uniqueID)}, ())
            if not device:
                LOGGER.error("uniqueID %s has no device ID", uniqueID)
                return
            areaEntry = self.area_reg._async_is_registered(hassArea)
            if not areaEntry:
                if areacreate != 'create':
                    LOGGER.debug("Area %s not registered and " + CONF_AREACREATE + " is not \"create\" - ignoring", hassArea)
                    return
                else:
                    LOGGER.debug("Creating new area %s", hassArea)
                    areaEntry = self.area_reg.async_create(hassArea)
            LOGGER.debug("assigning deviceid=%s area_id=%s" % (device.id, areaEntry.id))
            self.device_reg.async_update_device(device.id, area_id=areaEntry.id)
