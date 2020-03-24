"""Code to handle a Dynalite bridge."""

from typing import TYPE_CHECKING, Any, Callable, Dict, List

from dynalite_devices_lib.dynalite_devices import DynaliteDevices

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar, device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import CONF_ALL, CONF_HOST, ENTITY_PLATFORMS, LOGGER, CONF_AREA_CREATE, CONF_AREA_CREATE_MANUAL, CONF_AREA_CREATE_ASSIGN, CONF_AREA_CREATE_AUTO, DOMAIN

if TYPE_CHECKING:  # pragma: no cover
    from .dynalitebase import DynaliteBase


class DynaliteBridge:
    """Manages a single Dynalite bridge."""

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]) -> None:
        """Initialize the system based on host parameter."""
        self.hass = hass
        self.area = {}
        self.async_add_devices = {}
        self.waiting_devices = {}
        self.area_reg = None
        self.device_reg = None
        self.host = config[CONF_HOST]
        self.areacreate = config[CONF_AREA_CREATE].lower()
        # Configure the dynalite devices
        self.dynalite_devices = DynaliteDevices(
            new_device_func=self.add_devices_when_registered,
            update_device_func=self.update_device,
        )
        self.dynalite_devices.configure(config)

    async def async_setup(self) -> bool:
        """Set up a Dynalite bridge."""
        # Configure the dynalite devices
        LOGGER.debug("Setting up bridge - host %s", self.host)
        self.area_reg = await ar.async_get_registry(self.hass)
        self.device_reg = await dr.async_get_registry(self.hass)
        return await self.dynalite_devices.async_setup()

    def reload_config(self, config: Dict[str, Any]) -> None:
        """Reconfigure a bridge when config changes."""
        LOGGER.debug("Reloading bridge - host %s, config %s", self.host, config)
        self.dynalite_devices.configure(config)

    def update_signal(self, device: "DynaliteBase" = None) -> str:
        """Create signal to use to trigger entity update."""
        if device:
            signal = f"dynalite-update-{self.host}-{device.unique_id}"
        else:
            signal = f"dynalite-update-{self.host}"
        return signal

    @callback
    def update_device(self, device: "DynaliteBase") -> None:
        """Call when a device or all devices should be updated."""
        if device == CONF_ALL:
            # This is used to signal connection or disconnection, so all devices may become available or not.
            log_string = (
                "Connected" if self.dynalite_devices.connected else "Disconnected"
            )
            LOGGER.info("%s to dynalite host", log_string)
            async_dispatcher_send(self.hass, self.update_signal())
        else:
            async_dispatcher_send(self.hass, self.update_signal(device))

    @callback
    def register_add_devices(self, platform: str, async_add_devices: Callable) -> None:
        """Add an async_add_entities for a category."""
        self.async_add_devices[platform] = async_add_devices
        if platform in self.waiting_devices:
            self.async_add_devices[platform](self.waiting_devices[platform])

    def add_devices_when_registered(self, devices: List["DynaliteBase"]) -> None:
        """Add the devices to HA if the add devices callback was registered, otherwise queue until it is."""
        for platform in ENTITY_PLATFORMS:
            platform_devices = [
                device for device in devices if device.category == platform
            ]
            if platform in self.async_add_devices:
                self.async_add_devices[platform](platform_devices)
            else:  # handle it later when it is registered
                if platform not in self.waiting_devices:
                    self.waiting_devices[platform] = []
                self.waiting_devices[platform].extend(platform_devices)

    @property
    def available(self):
        return self.dynalite_devices.connected
        
    async def entity_added_to_ha(self, entity):
        """Call when an entity is added to HA so we can set its area."""
        if self.areacreate == CONF_AREA_CREATE_MANUAL:
            LOGGER.debug("area assignment set to manual - ignoring")
            return  # only need to update the areas if it is 'assign' or 'create'
        assert self.areacreate in [CONF_AREA_CREATE_ASSIGN, CONF_AREA_CREATE_AUTO]
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
                if self.areacreate != CONF_AREA_CREATE_AUTO:
                    LOGGER.debug(
                        "Area %s not registered and "
                        + CONF_AREA_CREATE
                        + ' is not "'
                        + CONF_AREA_CREATE_AUTO
                        + '" - ignoring',
                        hassArea,
                    )
                    return
                else:
                    LOGGER.debug("Creating new area %s", hassArea)
                    areaEntry = self.area_reg.async_create(hassArea)
            LOGGER.debug("assigning deviceid=%s area_id=%s" % (device.id, areaEntry.id))
            self.device_reg.async_update_device(device.id, area_id=areaEntry.id)
