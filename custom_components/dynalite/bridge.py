"""Code to handle a Hue bridge."""
import asyncio

from homeassistant import config_entries
from homeassistant.const import CONF_COVERS
from homeassistant.helpers import device_registry as dr
import pprint

from .const import DOMAIN, LOGGER, CONF_BRIDGES, DATA_CONFIGS, CONF_CHANNEL, CONF_AREA, CONF_PRESET, CONF_FACTOR, CONF_CHANNELTYPE
from .dynalite_lib.dynalite import Dynalite
from .light import DynaliteChannelLight
from .switch import DynaliteChannelSwitch, DynalitePresetSwitch
from .cover import DynaliteChannelCover


class DynaliteBridge:
    """Manages a single Dynalite bridge."""

    def __init__(self, hass, config_entry):
        """Initialize the system."""
        self.config_entry = config_entry
        self.hass = hass
        self.area = {}
        self.async_add_entities = {}
        self._added_channels = {}
        self._added_presets = {}

    @property
    def host(self):
        """Return the host of this bridge."""
        return self.config_entry.data["host"]

    async def async_setup(self, tries=0):
        """Set up a Dynalite bridge based on host parameter."""
        host = self.host
        hass = self.hass
        LOGGER.debug("bridge async_setup - %s" % pprint.pformat(self.config_entry.data))
        
        if (host not in hass.data[DATA_CONFIGS]):
            LOGGER.info("invalid host - %s" % host)
            return False
        
        config = hass.data[DATA_CONFIGS][host]
        self._dynalite = Dynalite(config=config, loop=hass.loop)
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
        # configure covers
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
        newSwitch = DynalitePresetSwitch(curArea, curPreset, curName, "preset", self, curDevice)
        self.async_add_entities['switch']([newSwitch])
        if (curArea not in self._added_presets):
            self._added_presets[curArea] = {}
        self._added_presets[curArea][curPreset] = newSwitch
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
        if int(curArea) in self._added_presets:
            for curPresetInArea in self._added_presets[int(curArea)]:
                self._added_presets[int(curArea)][curPresetInArea].try_schedule_ha()

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
        channelConfig=self.hass.data[DATA_CONFIGS][self.host]['area'][str(curArea)]['channel'][str(curChannel)] if str(curChannel) in self.hass.data[DATA_CONFIGS][self.host]['area'][str(curArea)]['channel'] else None
        LOGGER.debug("handleNewChannel - channelConfig=%s" % pprint.pformat(channelConfig))
        channelType = channelConfig[CONF_CHANNELTYPE] if channelConfig and CONF_CHANNELTYPE in channelConfig else 'light'
        channelType = channelType.lower()
        if channelType == 'light':
            newEntity = DynaliteChannelLight(curArea, curChannel, curName, channelType, self, curDevice)
            self.async_add_entities['light']([newEntity])
        elif channelType == 'switch' or channelType == 'hidden': # XXX fix the hidden part
            newEntity = DynaliteChannelSwitch(curArea, curChannel, curName, channelType, self, curDevice)
            if channelType == 'hidden':
                newEntity.set_hidden(True)
            self.async_add_entities['switch']([newEntity])
        elif channelType == 'cover':
            factor = channelConfig[CONF_FACTOR]
            newEntity = DynaliteChannelCover(curArea, curChannel, curName, channelType, factor, self, curDevice)
            self.async_add_entities['cover']([newEntity])
        else:
            LOGGER.info("unknown chnanel type %s - ignoring", channelType)
            return
        if (curArea not in self._added_channels):
            self._added_channels[curArea] = {}
        self._added_channels[curArea][curChannel] = newEntity
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
            if (int(curArea) in self._added_channels) and (int(curChannel) in self._added_channels[int(curArea)]):
                channelToSet = self._added_channels[int(curArea)][int(curChannel)]
                channelToSet.update_level(actual_level, target_level)
                #self.scheduleUpdateHAStateWhenAdded(channelToSet)
                channelToSet.try_schedule_ha() # to only call if it was already added to ha
        elif action == 'cmd':
            if (int(curArea) in self._added_channels) and (int(curChannel) in self._added_channels[int(curArea)]):
                self._added_channels[int(curArea)][int(curChannel)].try_schedule_ha()
        else:
            LOGGER.error("unknown action for channel change %s", action)
        

