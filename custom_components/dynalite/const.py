"""Constants for the Dynalite component."""
import logging

LOGGER = logging.getLogger(__package__)
DOMAIN = "dynalite"
DATA_CONFIGS = "dynalite_configs"

CONF_AREACREATE = "areacreate"
CONF_AREACREATE_MANUAL = "manual"
CONF_AREACREATE_ASSIGN = "assign"
CONF_AREACREATE_AUTO = "auto"
CONF_BRIDGES = "bridges"

ENTITY_CATEGORIES = ["light", "switch", "cover"]
DEFAULT_NAME = "dynalite"
DEFAULT_PORT = 12345
