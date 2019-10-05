"""Code to handle a Hue bridge."""
import asyncio
import pprint
import copy

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_COVERS, CONF_NAME, CONF_HOST
from homeassistant.helpers import device_registry as dr, area_registry as ar, discovery

from dynalite_lib.dynalite import Dynalite

from .const import (DOMAIN, LOGGER, CONF_BRIDGES, DATA_CONFIGS, CONF_CHANNEL, CONF_AREA, CONF_PRESET, CONF_FACTOR, CONF_CHANNELTYPE, CONF_HIDDENENTITY, CONF_TILTPERCENTAGE,
                    CONF_AREACREATE, CONF_AREAOVERRIDE, CONF_CHANNELCLASS, CONF_TEMPLATE, CONF_ROOM_ON, CONF_ROOM_OFF, DEFAULT_TEMPLATES, CONF_ROOM, DEFAULT_CHANNELTYPE,
                    CONF_AREA_CREATE_MANUAL, CONF_AREA_CREATE_ASSIGN, CONF_AREA_CREATE_AUTO, CONF_TEMPLATEOVERRIDE, DEFAULT_COVERCHANNELCLASS, DEFAULT_COVERFACTOR, CONF_TRIGGER,
                    CONF_CHANNELCOVER, CONF_NODEFAULT)
from .light import DynaliteChannelLight
from .switch import DynaliteChannelSwitch, DynalitePresetSwitch, DynaliteRoomPresetSwitch
from .cover import DynaliteChannelCover, DynaliteChannelCoverWithTilt

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
        self.added_channels = {}
        self.added_presets = {}
        self.added_room_switches = {}
        self.area_reg = None
        self.device_reg = None
        self.config = None
        self.futures = {}
        self._state = "Initializing" # XXX

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
        LOGGER.debug("bridge async_setup - %s" % pprint.pformat(self.config_entry.data))
        self.hass.loop.set_debug(True) # XXX
        if (host not in hass.data[DATA_CONFIGS]):
            LOGGER.info("invalid host - %s" % host)
            return False
        
        self.config = copy.deepcopy(hass.data[DATA_CONFIGS][host])
        # insert the templates
        if CONF_TEMPLATE not in self.config:
            LOGGER.debug(CONF_TEMPLATE + " not in config - using defaults")
            self.config[CONF_TEMPLATE] = DEFAULT_TEMPLATES
        else:
            for template in DEFAULT_TEMPLATES:
                if template not in self.config[CONF_TEMPLATE]:
                    LOGGER.debug("%s not in " + CONF_TEMPLATE + " using default", template)
                    self.config[CONF_TEMPLATE][template] = DEFAULT_TEMPLATES[template]
                else:
                    for param in DEFAULT_TEMPLATES[template]:
                        if param not in self.config[CONF_TEMPLATE][template]:
                            self.config[CONF_TEMPLATE][template][param] = DEFAULT_TEMPLATES[template][param]
        # add the entities implicitly defined by templates
        for curArea in self.config[CONF_AREA]:
            if CONF_TEMPLATE in self.config[CONF_AREA][curArea]:
                template = self.config[CONF_AREA][curArea][CONF_TEMPLATE]
                if template == CONF_ROOM:
                    self.config[CONF_AREA][curArea][CONF_NODEFAULT] = True
                    if CONF_PRESET not in self.config[CONF_AREA][curArea]:
                        self.config[CONF_AREA][curArea][CONF_PRESET] = {}
                    roomOn = self.getTemplateIndex(int(curArea), CONF_ROOM, CONF_ROOM_ON)
                    if str(roomOn) not in self.config[CONF_AREA][curArea][CONF_PRESET]:
                        self.config[CONF_AREA][curArea][CONF_PRESET][str(roomOn)] = {CONF_HIDDENENTITY: True}
                    roomOff = self.getTemplateIndex(int(curArea), CONF_ROOM, CONF_ROOM_OFF)
                    if str(roomOff) not in self.config[CONF_AREA][curArea][CONF_PRESET]:
                        self.config[CONF_AREA][curArea][CONF_PRESET][str(roomOff)] = {CONF_HIDDENENTITY: True}
                elif template == CONF_TRIGGER:
                    if CONF_PRESET not in self.config[CONF_AREA][curArea]:
                        self.config[CONF_AREA][curArea][CONF_PRESET] = {}
                    self.config[CONF_AREA][curArea][CONF_NODEFAULT] = True
                    trigger = self.getTemplateIndex(int(curArea), CONF_TRIGGER, CONF_TRIGGER)
                    if str(trigger) not in self.config[CONF_AREA][curArea][CONF_PRESET]:
                        self.config[CONF_AREA][curArea][CONF_PRESET][str(trigger)] = {CONF_HIDDENENTITY: False, CONF_NAME: self.config[CONF_AREA][curArea][CONF_NAME]}
                elif template == CONF_CHANNELCOVER:
                    self.config[CONF_AREA][curArea][CONF_NODEFAULT] = True
                    curChannel = self.getTemplateIndex(int(curArea), CONF_CHANNELCOVER, CONF_CHANNEL)
                    if CONF_CHANNEL not in self.config[CONF_AREA][curArea]:
                        self.config[CONF_AREA][curArea][CONF_CHANNEL] = {}
                    if str(curChannel) not in self.config[CONF_AREA][curArea][CONF_CHANNEL]:
                        self.config[CONF_AREA][curArea][CONF_CHANNEL][str(curChannel)] = {
                            CONF_NAME: self.config[CONF_AREA][curArea][CONF_NAME], 
                            CONF_CHANNELTYPE: 'cover', 
                            CONF_HIDDENENTITY: False
                        }
                    if self.getTemplateIndex(curArea, CONF_CHANNELCOVER, CONF_CHANNELCLASS):
                        self.config[CONF_AREA][curArea][CONF_CHANNEL][str(curChannel)][CONF_CHANNELCLASS] = self.getTemplateIndex(curArea, CONF_CHANNELCOVER, CONF_CHANNELCLASS)
                    if self.getTemplateIndex(curArea, CONF_CHANNELCOVER, CONF_FACTOR):
                        self.config[CONF_AREA][curArea][CONF_CHANNEL][str(curChannel)][CONF_FACTOR] = self.getTemplateIndex(curArea, CONF_CHANNELCOVER, CONF_FACTOR)
                    if self.getTemplateIndex(curArea, CONF_CHANNELCOVER, CONF_TILTPERCENTAGE):
                        self.config[CONF_AREA][curArea][CONF_CHANNEL][str(curChannel)][CONF_TILTPERCENTAGE] = self.getTemplateIndex(curArea, CONF_CHANNELCOVER, CONF_TILTPERCENTAGE)
        LOGGER.debug("bridge async_setup (after templates) - %s" % pprint.pformat(self.config))

        # Configure the dynalite object         
        self._dynalite = Dynalite(config=self.config, loop=hass.loop, logger=LOGGER)
        eventHandler = self._dynalite.addListener(
            listenerFunction=self.handleEvent)
        eventHandler.monitorEvent('*')
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
        self._dynalite.start()
        self._state = 'Connected' # XXX

        for category in ['light', 'switch', 'cover']:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(self.config_entry, category) # XXX maybe handle the race condition if need to use before init. not urgent
            )

        LOGGER.debug("XXX finished dynalite async_start")
        return True

    @callback
    def register_add_entities(self, category, async_add_entities):
        LOGGER.debug("XXX register_add_entities %s", category)
        self.async_add_entities[category] = async_add_entities
        if category in self.waiting_entities:
            self.async_add_entities[category](self.waiting_entities[category])
        if category == 'switch':
            self.hass.async_create_task(self.registerRooms())

    def add_entity_when_registered(self, category, entity):
        if category in self.async_add_entities:
            self.async_add_entities[category]([entity])
        else: # handle it later when it is registered
            if category not in self.waiting_entities:
                self.waiting_entities[category] = []
            self.waiting_entities[category].append(entity)

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

    @callback
    def getTemplateIndex(self, area, template, conf):
        my_template = self.config[CONF_TEMPLATE][template] # always defined either by the user or by the defaults
        index = None
        if conf in my_template:
            index = my_template[conf]
        try:
            index = self.config[CONF_AREA][str(area)][CONF_TEMPLATEOVERRIDE][conf]
        except KeyError:
            pass
        return index

    @callback
    def setPresetIfReady(self, area, template, conf, deviceNum, entity):
        preset = self.getTemplateIndex(area, template, conf)
        if not preset:
            return
        try:
            device = self.added_presets[int(area)][int(preset)]
            entity.set_device(deviceNum, device)
        except KeyError:
            pass

    async def registerRooms(self):
        room_template = self.config[CONF_TEMPLATE][CONF_ROOM] # always defined either by the user or by the defaults
        try:
            preset_on = room_template[CONF_ROOM_ON]
            preset_off = room_template[CONF_ROOM_OFF]
        except KeyError:
            LOGGER.error(CONF_ROOM + " template must have " + CONF_ROOM_ON + " and " + CONF_ROOM_OFF + " need to handle in config_validation") # XXX handle in cv
            return
        for curArea in self.config[CONF_AREA]:
            if CONF_TEMPLATE in self.config[CONF_AREA][curArea] and self.config[CONF_AREA][curArea][CONF_TEMPLATE] == CONF_ROOM:
                newEntity = DynaliteRoomPresetSwitch(curArea, self.config[CONF_AREA][curArea][CONF_NAME], self.getHassArea(curArea), self)
                self.added_room_switches[int(curArea)] = newEntity
                self.setPresetIfReady(curArea, CONF_ROOM, CONF_ROOM_ON, 1, newEntity)
                self.setPresetIfReady(curArea, CONF_ROOM, CONF_ROOM_OFF, 2, newEntity)
                self.add_entity_when_registered('switch', newEntity) 

    @callback
    def handleEvent(self, event=None, dynalite=None):
        LOGGER.debug("handleEvent - type=%s event=%s" % (event.eventType, pprint.pformat(event.data)))
        return

    @callback
    def getHassArea(self, area):
        if str(area) not in self.config[CONF_AREA]:
            LOGGER.error("getHassArea - we should not get here")
            raise BridgeError("getHassArea - area " + str(area) + "is not in config")
        areaConfig=self.config[CONF_AREA][str(area)]
        hassArea = areaConfig[CONF_NAME]
        if CONF_AREAOVERRIDE in areaConfig:
            overrideArea = areaConfig[CONF_AREAOVERRIDE]
            hassArea = overrideArea if overrideArea.lower() != 'none' else ''
        return hassArea
        
    @callback
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

        if str(curArea) not in self.config[CONF_AREA]:
            LOGGER.debug("adding area " + str(curArea) + " that is not in config")
            self.config[CONF_AREA][str(curArea)] = {CONF_NAME: "Area " + str(curArea)}
        
        try:
            curName = self.config[CONF_AREA][str(curArea)][CONF_PRESET][str(curPreset)][CONF_NAME] # If the name is explicitly defined, use it
        except KeyError:
            presetName = "Preset " + str(curPreset)
            if CONF_NODEFAULT not in self.config[CONF_AREA][str(curArea)] or not self.config[CONF_AREA][str(curArea)][CONF_NODEFAULT]:
                try:
                    presetName = self.config[CONF_PRESET][str(curPreset)][CONF_NAME] # XXX need to check for nodefault flag
                except KeyError:
                    pass
            curName = self.config[CONF_AREA][str(curArea)][CONF_NAME] + " " + presetName # If not explicitly defined, use "areaname presetname"
        curDevice = self._dynalite.devices[CONF_AREA][curArea].preset[curPreset]
        newEntity = DynalitePresetSwitch(curArea, curPreset, curName, self.getHassArea(curArea), self, curDevice)
        self.add_entity_when_registered('switch', newEntity)
        if (curArea not in self.added_presets):
            self.added_presets[curArea] = {}
        self.added_presets[curArea][curPreset] = newEntity

        try:
            hidden = self.config[CONF_AREA][str(curArea)][CONF_PRESET][str(curPreset)][CONF_HIDDENENTITY]
        except KeyError:
            hidden = False

        try:
            template = self.config[CONF_AREA][str(curArea)][CONF_TEMPLATE] # templates may make some elements hidden
            if template == CONF_ROOM:
                hidden = True # in a template room, the presets will all be in the room switch
                if int(curArea) in self.added_room_switches: # if it is not there yet, it will be added when the room switch will be created
                    roomSwitch=self.added_room_switches[int(curArea)]
                    roomTemplate = self.config[CONF_TEMPLATE][CONF_ROOM]
                    if int(curPreset) == int(self.getTemplateIndex(curArea, CONF_ROOM, CONF_ROOM_ON)):
                        roomSwitch.set_device(1, newEntity)
                    if int(curPreset) == int(self.getTemplateIndex(curArea, CONF_ROOM, CONF_ROOM_OFF)):
                        roomSwitch.set_device(2, newEntity)
            elif template == CONF_TRIGGER:
                triggerPreset = self.getTemplateIndex(curArea, template, CONF_TRIGGER)
                if int(curPreset) != int(triggerPreset):
                  hidden = True
            elif template in [CONF_HIDDENENTITY, CONF_CHANNELCOVER]:
                hidden = True
            else:
                LOGGER.error("Unknown template " + template + ". Should have been caught in config_validation")
        except KeyError:
            pass
        
        if hidden:
            newEntity.set_hidden(True)   
        LOGGER.debug("Creating Dynalite preset area=%s preset=%s name=%s" % (curArea, curPreset, curName))

    @callback
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

    @callback
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

        if str(curArea) not in self.config[CONF_AREA]:
            LOGGER.debug("adding area " + str(curArea) + " that is not in config")
            self.config[CONF_AREA][str(curArea)] = {CONF_NAME: "Area " + str(curArea)}
        
        try:
            curName = self.config[CONF_AREA][str(curArea)][CONF_CHANNEL][str(curChannel)][CONF_NAME] # If the name is explicitly defined, use it
        except (KeyError, TypeError):
            curName = self.config[CONF_AREA][str(curArea)][CONF_NAME] + " Channel " + str(curChannel) # If not explicitly defined, use "areaname Channel X"
        curDevice = self._dynalite.devices[CONF_AREA][curArea].channel[curChannel]
        try:
            channelConfig=self.config[CONF_AREA][str(curArea)][CONF_CHANNEL][str(curChannel)]
        except KeyError:
            channelConfig = None
        LOGGER.debug("handleNewChannel - channelConfig=%s" % pprint.pformat(channelConfig))
        channelType = channelConfig[CONF_CHANNELTYPE].lower() if channelConfig and CONF_CHANNELTYPE in channelConfig else DEFAULT_CHANNELTYPE
        hassArea = self.getHassArea(curArea)
        if channelType == 'light':
            newEntity = DynaliteChannelLight(curArea, curChannel, curName, channelType, hassArea, self, curDevice)
            self.add_entity_when_registered('light', newEntity)
        elif channelType == 'switch':
            newEntity = DynaliteChannelSwitch(curArea, curChannel, curName, channelType, hassArea, self, curDevice)
            self.add_entity_when_registered('switch', newEntity)
        elif channelType == 'cover':
            factor = channelConfig[CONF_FACTOR] if CONF_FACTOR in channelConfig else DEFAULT_COVERFACTOR
            deviceClass = channelConfig[CONF_CHANNELCLASS] if CONF_CHANNELCLASS in channelConfig else DEFAULT_COVERCHANNELCLASS
            if CONF_TILTPERCENTAGE in channelConfig:
                newEntity = DynaliteChannelCoverWithTilt(curArea, curChannel, curName, channelType, deviceClass, factor, channelConfig[CONF_TILTPERCENTAGE], hassArea, self, curDevice)
            else:
                newEntity = DynaliteChannelCover(curArea, curChannel, curName, channelType, deviceClass, factor, hassArea, self, curDevice)
            self.add_entity_when_registered('cover', newEntity)
        else:
            LOGGER.info("unknown chnanel type %s - ignoring", channelType)
            return
        if (curArea not in self.added_channels):
            self.added_channels[curArea] = {}
        self.added_channels[curArea][curChannel] = newEntity
        if channelConfig and channelConfig[CONF_HIDDENENTITY]:
            newEntity.set_hidden(True)   
        if self.config[CONF_AREA][str(curArea)].get(CONF_TEMPLATE) == CONF_HIDDENENTITY:
            newEntity.set_hidden(True)
        LOGGER.debug("Creating Dynalite channel area=%s channel=%s name=%s" % (curArea, curChannel, curName))

    @callback
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
        elif action == 'cmd':
            target_level = (255 - event.data['target_level']) / 254
            actual_level = target_level # when there is only a "set channel level" command, assume that this is both the actual and the target
        else:
            LOGGER.error("unknown action for channel change %s", action)
            return
        try:
            channelToSet = self.added_channels[int(curArea)][int(curChannel)]
            channelToSet.update_level(actual_level, target_level)
            channelToSet.try_schedule_ha() # to only call if it was already added to ha
        except KeyError:
            pass
        
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
            device = self.device_reg.async_get_device({(DOMAIN, uniqueID)}, ())
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
