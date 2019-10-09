"""Constants for the Dynalite component."""
import logging
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME, CONF_COVERS
from homeassistant.components.cover import DEVICE_CLASS_SHUTTER

LOGGER = logging.getLogger(__package__)
DOMAIN = "dynalite"

from dynalite_devices_lib import (
    CONF_CHANNEL,
    CONF_AREA,
    CONF_PRESET,
    CONF_FACTOR,
    CONF_CHANNELTYPE,
    CONF_HIDDENENTITY,
    CONF_TILTPERCENTAGE,
    CONF_AREAOVERRIDE,
    CONF_CHANNELCLASS,
    CONF_TEMPLATE,
    CONF_ROOM_ON,
    CONF_ROOM_OFF,
    DEFAULT_TEMPLATES,
    CONF_ROOM,
    DEFAULT_CHANNELTYPE,
    CONF_TEMPLATEOVERRIDE,
    DEFAULT_COVERCHANNELCLASS,
    DEFAULT_COVERFACTOR,
    CONF_TRIGGER,
    CONF_CHANNELCOVER,
    CONF_NODEFAULT,
    CONF_LOGLEVEL,
    CONF_FADE,
    CONF_DEFAULT,
    CONF_POLLTIMER,
    CONF_AUTODISCOVER,
    CONF_ALL,
)

CONF_BRIDGES = "bridges"
CONF_AREACREATE = "areacreate"
CONF_AREA_CREATE_MANUAL = "manual"
CONF_AREA_CREATE_ASSIGN = "assign"
CONF_AREA_CREATE_AUTO = "auto"

DATA_CONFIGS = "dynalite_configs"
ENTITY_CATEGORIES = ["light", "switch", "cover"]

DEFAULT_NAME = "dynalite"
DEFAULT_PORT = 12345
DEFAULT_LOGGING = "info"
