"""Support for the Dynalite networks."""
import ipaddress
import logging
import pprint

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_FILENAME, CONF_HOST, CONF_PORT, CONF_NAME, CONF_ICON, CONF_COVERS
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import (DOMAIN, CONF_BRIDGES, DATA_CONFIGS, LOGGER, CONF_LOGLEVEL, CONF_AREA, CONF_PRESET, CONF_CHANNEL, CONF_NODEFAULT,
                    CONF_FADE, CONF_DEFAULT, CONF_CHANNELTYPE, CONF_FACTOR, CONF_AUTODISCOVER)
from .bridge import DynaliteBridge

# Loading the config flow file will register the flow
from .config_flow import configured_hosts

DEFAULT_NAME = 'dynalite'
DEFAULT_PORT = 12345
DEFAULT_LOGGING = 'info'
DEFAULT_ICON = 'mdi:lightbulb-outline'
DEFAULT_CHANNELTYPE = 'light'
DEFAULT_COVERDURATION = 120 # 2 min to open or close cover
DEFAULT_COVERFACTOR = 1.0 # cover goes from closed(0.0) to open (1.0). If it needs less than the range, use a lower number

PRESET_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_FADE): cv.string # XXX may want this for channel as well
})

PRESET_SCHEMA = vol.Schema({
    cv.slug: vol.Any(PRESET_DATA_SCHEMA, None)
})

CHANNEL_DATA_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_CHANNELTYPE, default=DEFAULT_CHANNELTYPE): cv.string,
    vol.Optional(CONF_FACTOR, default=DEFAULT_COVERFACTOR): cv.small_float
})

CHANNEL_SCHEMA = vol.Schema({
    cv.slug: vol.Any(CHANNEL_DATA_SCHEMA, None)
})

AREA_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Optional(CONF_FADE): cv.string,
    vol.Optional(CONF_NODEFAULT): cv.boolean,
    vol.Optional(CONF_PRESET): PRESET_SCHEMA,
    vol.Optional(CONF_CHANNEL): CHANNEL_SCHEMA
})

AREA_SCHEMA = vol.Schema({
    cv.slug: vol.Any(AREA_DATA_SCHEMA, None)
})

PLATFORM_DEFAULTS_SCHEMA = vol.Schema({
    vol.Optional(CONF_FADE): cv.string,
})

BRIDGE_CONFIG_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_LOGLEVEL, default=DEFAULT_LOGGING): cv.string,
    vol.Optional(CONF_AUTODISCOVER, default=True):cv.boolean,
    vol.Optional(CONF_AREA): AREA_SCHEMA,
    vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.string,
    vol.Optional(CONF_DEFAULT): PLATFORM_DEFAULTS_SCHEMA,
    vol.Optional(CONF_PRESET): PRESET_SCHEMA,
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
                    "host": bridge_conf[CONF_HOST],
                },
            )
        )


    return True


async def async_setup_entry(hass, entry):
    """Set up a bridge from a config entry."""
    LOGGER.debug("__init async_setup_entry %s", pprint.pformat(entry.data))
    host = entry.data["host"]
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
    bridge = hass.data[DOMAIN].pop(entry.data["host"])
    return await bridge.async_reset()
