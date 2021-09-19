from homeassistant import core, loader
from .const import DOMAIN

async def test_custom_component_name(hass, enable_custom_integrations):
    """Test that we are able to load the custom component."""

    integration = await loader.async_get_integration(hass, DOMAIN)
    platform = integration.get_platform("light")
    assert platform.__name__ == "custom_components.dynalite2.light"
    assert platform.__package__ == "custom_components.dynalite2"


