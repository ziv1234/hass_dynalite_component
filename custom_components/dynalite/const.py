"""Constants for the Dynalite component."""
import logging

LOGGER = logging.getLogger(__package__)
DOMAIN = "dynalite"

CONF_BRIDGES = "bridges"
CONF_LOGLEVEL = 'log_level'
CONF_AREA = 'area'
CONF_PRESET = 'preset'
CONF_CHANNEL = 'channel'
CONF_NODEFAULT = 'nodefault'
CONF_FADE = 'fade'
CONF_DEFAULT = 'default'
CONF_CHANNELTYPE = 'type'
CONF_CHANNELCLASS = 'class'
CONF_HIDDENENTITY = 'hidden'
CONF_FACTOR = 'factor'
CONF_TILTPERCENTAGE = 'tilt'
CONF_AUTODISCOVER = 'autodiscover'
CONF_POLLTIMER = 'polltimer'
CONF_AREACREATE = 'areacreate'
CONF_AREAOVERRIDE = 'areaoverride'
CONF_ROOM_ON = 'room_on'
CONF_ROOM_OFF = 'room_off'
CONF_TEMPLATE = 'template'

CONF_ROOM = 'room'
CONF_TRIGGER = 'trigger'
CONF_AREA_CREATE_MANUAL = 'manual'
CONF_AREA_CREATE_ASSIGN = 'assign'
CONF_AREA_CREATE_AUTO = 'auto'

DATA_CONFIGS = "dynalite_configs"

DEFAULT_NAME = 'dynalite'
DEFAULT_PORT = 12345
DEFAULT_LOGGING = 'info'
DEFAULT_ICON = 'mdi:lightbulb-outline'
DEFAULT_CHANNELTYPE = 'light'
DEFAULT_COVERDURATION = 120 # 2 min to open or close cover
DEFAULT_COVERFACTOR = 1.0 # cover goes from closed(0.0) to open (1.0). If it needs less than the range, use a lower number
DEFAULT_TEMPLATES = {'room':{CONF_ROOM_ON: '1', CONF_ROOM_OFF: '4'}}
