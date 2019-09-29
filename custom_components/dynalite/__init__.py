"""Support for the Dynalite networks."""
import ipaddress
import logging
import pprint

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_FILENAME, CONF_HOST, CONF_PORT, CONF_NAME, CONF_ICON, CONF_COVERS
from homeassistant.helpers import config_validation as cv
from homeassistant.components.cover import DEVICE_CLASSES_SCHEMA, DEVICE_CLASS_SHUTTER

from .const import (DOMAIN, CONF_BRIDGES, DATA_CONFIGS, LOGGER, CONF_LOGLEVEL, CONF_AREA, CONF_PRESET, CONF_CHANNEL, CONF_NODEFAULT,
                    CONF_FADE, CONF_DEFAULT, CONF_CHANNELTYPE, CONF_HIDDENENTITY, CONF_FACTOR, CONF_TILTPERCENTAGE, CONF_AUTODISCOVER, CONF_POLLTIMER,
                    CONF_AREACREATE, CONF_AREAOVERRIDE, CONF_CHANNELCLASS, CONF_TEMPLATE, CONF_ROOM_OFF, CONF_ROOM_ON, CONF_TRIGGER,
                    CONF_AREA_CREATE_MANUAL, CONF_AREA_CREATE_ASSIGN, CONF_AREA_CREATE_AUTO, CONF_TEMPLATEOVERRIDE,
                    DEFAULT_NAME, DEFAULT_PORT, DEFAULT_LOGGING, DEFAULT_ICON, DEFAULT_CHANNELTYPE, DEFAULT_COVERFACTOR,
                    DEFAULT_TEMPLATES, CONF_ROOM)
from .bridge import DynaliteBridge

# Loading the config flow file will register the flow
from .config_flow import configured_hosts

DEFAULT_TEMPLATE_NAMES = [t for t in DEFAULT_TEMPLATES]

TEMPLATE_ROOM_SCHEMA = vol.Schema({
    vol.Optional(CONF_ROOM_ON): cv.slug,
    vol.Optional(CONF_ROOM_OFF): cv.slug,
})

TEMPLATE_TRIGGER_SCHEMA = cv.slug

TEMPLATE_CHANNELCOVER_SCHEMA = vol.Schema({
    vol.Optional(CONF_CHANNEL): cv.slug,
    vol.Optional(CONF_CHANNELCLASS): DEVICE_CLASSES_SCHEMA,
    vol.Optional(CONF_FACTOR): cv.small_float,
    vol.Optional(CONF_TILTPERCENTAGE): cv.small_float
})

TEMPLATE_DATA_SCHEMA = vol.Any(TEMPLATE_ROOM_SCHEMA, TEMPLATE_TRIGGER_SCHEMA, TEMPLATE_CHANNELCOVER_SCHEMA)

PRESET_DATA_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_FADE): cv.string,
    vol.Optional(CONF_HIDDENENTITY, default=False): cv.boolean
})

PRESET_SCHEMA = vol.Schema({
    cv.slug: vol.Any(PRESET_DATA_SCHEMA, None)
})

def check_channel_data_schema(conf):
    if conf[CONF_CHANNELTYPE] != 'cover':
        for param in [CONF_CHANNELCLASS, CONF_FACTOR, CONF_TILTPERCENTAGE]:
            if param in conf:
                raise vol.Invalid("parameter " + param + " is only valid for \'cover\' type channels")
    return conf

CHANNEL_DATA_SCHEMA = vol.Schema(vol.All({
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_FADE): cv.string,
    vol.Optional(CONF_CHANNELTYPE, default=DEFAULT_CHANNELTYPE): vol.Any('light','switch','cover'),
    vol.Optional(CONF_CHANNELCLASS): DEVICE_CLASSES_SCHEMA,
    vol.Optional(CONF_HIDDENENTITY, default=False): cv.boolean,
    vol.Optional(CONF_FACTOR): cv.small_float,
    vol.Optional(CONF_TILTPERCENTAGE): cv.small_float
}, check_channel_data_schema))

CHANNEL_SCHEMA = vol.Schema({
    cv.slug: vol.Any(CHANNEL_DATA_SCHEMA, None)
})

def check_area_data_schema(conf):
    if CONF_TEMPLATE in conf and conf[CONF_TEMPLATE] not in DEFAULT_TEMPLATES:
        raise vol.Invalid(conf[CONF_TEMPLATE] + " is not a valid template name. Possible names are: " + pprint.pformat(DEFAULT_TEMPLATE_NAMES))

    if CONF_TEMPLATEOVERRIDE in conf and False:
        if CONF_TEMPLATE not in conf:
            raise vol.Invalid(CONF_TEMPLATEOVERRIDE + " may only be present when " + CONF_TEMPLATE + " is defined")
        template = conf[CONF_TEMPLATE]
        if template == CONF_ROOM:
            TEMPLATE_ROOM_SCHEMA(conf[CONF_TEMPLATEOVERRIDE])
        elif template == CONF_TRIGGER:
            TEMPLATE_TRIGGER_SCHEMA(conf[CONF_TEMPLATEOVERRIDE])
        else:
            raise vol.Invalid("Unknown template type " + template)
    return conf

AREA_DATA_SCHEMA = vol.Schema(vol.All({
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_TEMPLATE): cv.string,
    vol.Optional(CONF_TEMPLATEOVERRIDE): TEMPLATE_DATA_SCHEMA,
    vol.Optional(CONF_FADE): cv.string,
    vol.Optional(CONF_NODEFAULT): cv.boolean,
    vol.Optional(CONF_AREAOVERRIDE): cv.string,
    vol.Optional(CONF_PRESET): PRESET_SCHEMA,
    vol.Optional(CONF_CHANNEL): CHANNEL_SCHEMA
}, check_area_data_schema))

AREA_SCHEMA = vol.Schema({
    cv.slug: vol.Any(AREA_DATA_SCHEMA, None)
})

PLATFORM_DEFAULTS_SCHEMA = vol.Schema({
    vol.Optional(CONF_FADE): cv.string,
})

def check_template_schema(conf):
    for template in conf:
        if template == CONF_ROOM:
            TEMPLATE_ROOM_SCHEMA(conf[template])
    return conf

TEMPLATE_SCHEMA = vol.Schema({
    cv.string: vol.Any(TEMPLATE_DATA_SCHEMA, None)
})

BRIDGE_CONFIG_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_LOGLEVEL, default=DEFAULT_LOGGING): cv.string,
    vol.Optional(CONF_AUTODISCOVER, default=True): cv.boolean,
    vol.Optional(CONF_AREACREATE, default=CONF_AREA_CREATE_MANUAL): vol.Any(CONF_AREA_CREATE_MANUAL, CONF_AREA_CREATE_ASSIGN, CONF_AREA_CREATE_AUTO),
    vol.Optional(CONF_POLLTIMER, default=1.0): vol.Coerce(float),
    vol.Optional(CONF_AREA): AREA_SCHEMA,
    vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
    vol.Optional(CONF_DEFAULT): PLATFORM_DEFAULTS_SCHEMA,
    vol.Optional(CONF_PRESET): PRESET_SCHEMA,
    vol.Optional(CONF_TEMPLATE, default=DEFAULT_TEMPLATES): TEMPLATE_SCHEMA
})

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_BRIDGES): vol.All(
                    cv.ensure_list, [BRIDGE_CONFIG_SCHEMA]
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass, config):
    """Set up the Dynalite platform."""
    conf = config.get(DOMAIN)
    LOGGER.debug("Setting up dynalite component config = %s", pprint.pformat(conf))

    if conf is None:
        conf = {}

    hass.data[DOMAIN] = {}
    hass.data[DATA_CONFIGS] = {}

    configured = configured_hosts(hass)

    # User has configured bridges
    if CONF_BRIDGES not in conf:
        return True

    bridges = conf[CONF_BRIDGES]

    for bridge_conf in bridges:
        host = bridge_conf[CONF_HOST]
        LOGGER.debug("async_setup host=%s conf=%s" % (host, pprint.pformat(bridge_conf)))

        # Store config in hass.data so the config entry can find it
        hass.data[DATA_CONFIGS][host] = bridge_conf

        if host in configured:
            LOGGER.debug("async_setup host=%s already configured" % host)
            continue

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data={
                    CONF_HOST: bridge_conf[CONF_HOST],
                },
            )
        )
    return True


async def async_setup_entry(hass, entry):
    """Set up a bridge from a config entry."""
    LOGGER.debug("__init async_setup_entry %s", pprint.pformat(entry.data))
    host = entry.data[CONF_HOST]
    config = hass.data[DATA_CONFIGS].get(host)

    if config is None:
        LOGGER.error("__init async_setup_entry empty config for host %s", host)

    bridge = DynaliteBridge(hass, entry)

    if not await bridge.async_setup():
        LOGGER.error("bridge.async_setup failed")
        return False

    hass.data[DOMAIN][host] = bridge
    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    LOGGER.error("async_unload_entry %s", pprint.pformat(entry.data))
    bridge = hass.data[DOMAIN].pop(entry.data[CONF_HOST])
    return await bridge.async_reset()
