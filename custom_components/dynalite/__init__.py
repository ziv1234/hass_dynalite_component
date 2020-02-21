"""Support for the Dynalite networks."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

# Loading the config flow file will register the flow
from .bridge import DynaliteBridge
from .const import (
    CONF_ACTIVE,
    CONF_ACTIVE_INIT,
    CONF_ACTIVE_OFF,
    CONF_ACTIVE_ON,
    CONF_AREA,
    CONF_AUTO_DISCOVER,
    CONF_BRIDGES,
    CONF_CHANNEL,
    CONF_CHANNEL_CLASS,
    CONF_CHANNEL_COVER,
    CONF_CHANNEL_TYPE,
    CONF_CLOSE_PRESET,
    CONF_DEFAULT,
    CONF_DURATION,
    CONF_FADE,
    CONF_NAME,
    CONF_NODEFAULT,
    CONF_OPEN_PRESET,
    CONF_POLLTIMER,
    CONF_PORT,
    CONF_PRESET,
    CONF_ROOM_OFF,
    CONF_ROOM_ON,
    CONF_STOP_PRESET,
    CONF_TEMPLATE,
    CONF_TILT_TIME,
    CONF_TRIGGER,
    DEFAULT_CHANNEL_TYPE,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_TEMPLATES,
    DOMAIN,
    ENTITY_PLATFORMS,
    LOGGER,
    CONF_AREA_CREATE,
    CONF_AREA_CREATE_AUTO,
    CONF_AREA_CREATE_ASSIGN,
    CONF_AREA_CREATE_MANUAL,
    CONF_AREA_OVERRIDE
)


def num_string(value):
    """Test if value is a string of digits, aka an integer."""
    new_value = str(value)
    if new_value.isdigit():
        return new_value
    raise vol.Invalid("Not a string with numbers")


CHANNEL_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_FADE): vol.Coerce(float),
        vol.Optional(CONF_CHANNEL_TYPE, default=DEFAULT_CHANNEL_TYPE): vol.Any(
            "light", "switch"
        ),
    }
)

CHANNEL_SCHEMA = vol.Schema({num_string: CHANNEL_DATA_SCHEMA})

PRESET_DATA_SCHEMA = vol.Schema(
    {vol.Optional(CONF_NAME): cv.string, vol.Optional(CONF_FADE): vol.Coerce(float)}
)

PRESET_SCHEMA = vol.Schema({num_string: vol.Any(PRESET_DATA_SCHEMA, None)})


TEMPLATE_ROOM_SCHEMA = vol.Schema(
    {vol.Optional(CONF_ROOM_ON): num_string, vol.Optional(CONF_ROOM_OFF): num_string}
)

TEMPLATE_TRIGGER_SCHEMA = vol.Schema({vol.Optional(CONF_TRIGGER): num_string})

TEMPLATE_TIMECOVER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CHANNEL_COVER): num_string,
        vol.Optional(CONF_CHANNEL_CLASS): cv.string,
        vol.Optional(CONF_OPEN_PRESET): num_string,
        vol.Optional(CONF_CLOSE_PRESET): num_string,
        vol.Optional(CONF_STOP_PRESET): num_string,
        vol.Optional(CONF_DURATION): vol.Coerce(float),
        vol.Optional(CONF_TILT_TIME): vol.Coerce(float),
    }
)

TEMPLATE_DATA_SCHEMA = vol.Any(
    TEMPLATE_ROOM_SCHEMA, TEMPLATE_TRIGGER_SCHEMA, TEMPLATE_TIMECOVER_SCHEMA
)

TEMPLATE_SCHEMA = vol.Schema({str: TEMPLATE_DATA_SCHEMA})


def validate_area(config):
    """Validate that template parameters are only used if area is using the relevant template."""
    conf_set = set()
    for template in DEFAULT_TEMPLATES:
        for conf in DEFAULT_TEMPLATES[template]:
            conf_set.add(conf)
    if config.get(CONF_TEMPLATE):
        for conf in DEFAULT_TEMPLATES[config[CONF_TEMPLATE]]:
            conf_set.remove(conf)
    for conf in conf_set:
        if config.get(conf):
            raise vol.Invalid(
                f"{conf} cannot should not be part of area {config[CONF_NAME]} config"
            )
    return config


AREA_DATA_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Required(CONF_NAME): cv.string,
            vol.Optional(CONF_TEMPLATE): cv.string,
            vol.Optional(CONF_FADE): vol.Coerce(float),
            vol.Optional(CONF_NODEFAULT): vol.Coerce(bool),
            vol.Optional(CONF_AREA_OVERRIDE): cv.string,
            vol.Optional(CONF_CHANNEL): CHANNEL_SCHEMA,
            vol.Optional(CONF_PRESET): PRESET_SCHEMA,
            # the next ones can be part of the templates
            vol.Optional(CONF_ROOM_ON): num_string,
            vol.Optional(CONF_ROOM_OFF): num_string,
            vol.Optional(CONF_TRIGGER): num_string,
            vol.Optional(CONF_CHANNEL_COVER): num_string,
            vol.Optional(CONF_CHANNEL_CLASS): cv.string,
            vol.Optional(CONF_OPEN_PRESET): num_string,
            vol.Optional(CONF_CLOSE_PRESET): num_string,
            vol.Optional(CONF_STOP_PRESET): num_string,
            vol.Optional(CONF_DURATION): vol.Coerce(float),
            vol.Optional(CONF_TILT_TIME): vol.Coerce(float),
        },
        validate_area,
    )
)

AREA_SCHEMA = vol.Schema({num_string: vol.Any(AREA_DATA_SCHEMA, None)})

PLATFORM_DEFAULTS_SCHEMA = vol.Schema({vol.Optional(CONF_FADE): vol.Coerce(float)})


BRIDGE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_AUTO_DISCOVER, default=False): vol.Coerce(bool),
        vol.Optional(CONF_ACTIVE, default=CONF_ACTIVE_OFF): vol.Any(
            CONF_ACTIVE_ON, CONF_ACTIVE_OFF, CONF_ACTIVE_INIT, bool
        ),
        vol.Optional(CONF_POLLTIMER, default=1.0): vol.Coerce(float),
        vol.Optional(CONF_AREA_CREATE, default=CONF_AREA_CREATE_MANUAL): vol.Any(
            CONF_AREA_CREATE_MANUAL, CONF_AREA_CREATE_ASSIGN, CONF_AREA_CREATE_AUTO
        ),
        vol.Optional(CONF_AREA): AREA_SCHEMA,
        vol.Optional(CONF_DEFAULT): PLATFORM_DEFAULTS_SCHEMA,
        vol.Optional(CONF_PRESET): PRESET_SCHEMA,
        vol.Optional(CONF_TEMPLATE, default=DEFAULT_TEMPLATES): TEMPLATE_SCHEMA,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {vol.Optional(CONF_BRIDGES): vol.All(cv.ensure_list, [BRIDGE_SCHEMA])}
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up the Dynalite platform."""

    conf = config.get(DOMAIN)
    LOGGER.debug("Setting up dynalite component config = %s", conf)

    if conf is None:
        conf = {}

    hass.data[DOMAIN] = {}

    # User has configured bridges
    if CONF_BRIDGES not in conf:
        return True

    bridges = conf[CONF_BRIDGES]

    for bridge_conf in bridges:
        host = bridge_conf[CONF_HOST]
        LOGGER.debug("Starting config entry flow host=%s conf=%s", host, bridge_conf)

        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_IMPORT},
                data=bridge_conf,
            )
        )

    return True


async def async_setup_entry(hass, entry):
    """Set up a bridge from a config entry."""
    LOGGER.debug("Setting up entry %s", entry.data)

    bridge = DynaliteBridge(hass, entry.data)

    if not await bridge.async_setup():
        LOGGER.error("Could not set up bridge for entry %s", entry.data)
        return False

    if not await bridge.try_connection():
        LOGGER.error("Could not connect with entry %s", entry)
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = bridge

    for platform in ENTITY_PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )
    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    LOGGER.debug("Unloading entry %s", entry.data)
    hass.data[DOMAIN].pop(entry.entry_id)
    result = await hass.config_entries.async_forward_entry_unload(entry, "light")
    return result
