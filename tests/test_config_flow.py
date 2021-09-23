"""Test Dynalite config flow."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant import config_entries
from homeassistant.components import dynalite

from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import DOMAIN

@pytest.mark.parametrize(
    "first_con, second_con,exp_type, exp_result, exp_reason",
    [
        (True, True, "create_entry", config_entries.ConfigEntryState.LOADED, ""),
        (False, False, "abort", None, "no_connection"),
        (True, False, "create_entry", config_entries.ConfigEntryState.SETUP_RETRY, ""),
    ],
)
async def test_flow(hass, enable_custom_integrations, first_con, second_con, exp_type, exp_result, exp_reason):
    """Run a flow with or without errors and return result."""
    host = "1.2.3.4"
    with patch(
        "custom_components.dynalite2.bridge.DynaliteDevices.async_setup",
        side_effect=[first_con, second_con],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={dynalite.CONF_HOST: host},
        )
        await hass.async_block_till_done()
    assert result["type"] == exp_type
    if exp_result:
        assert result["result"].state == exp_result
    if exp_reason:
        assert result["reason"] == exp_reason


async def test_existing(hass, enable_custom_integrations):
    """Test when the entry exists with the same config."""
    host = "1.2.3.4"
    MockConfigEntry(
        domain=DOMAIN, data={dynalite.CONF_HOST: host}, version=2
    ).add_to_hass(hass)
    with patch(
        "custom_components.dynalite2.bridge.DynaliteDevices.async_setup",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={dynalite.CONF_HOST: host},
        )
    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"


async def test_existing_update(hass, enable_custom_integrations):
    """Test when the entry exists with a different config."""
    host = "1.2.3.4"
    port1 = 7777
    port2 = 8888
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={dynalite.CONF_HOST: host, dynalite.CONF_PORT: port1},
        version=2,
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.dynalite2.bridge.DynaliteDevices"
    ) as mock_dyn_dev:
        mock_dyn_dev().async_setup = AsyncMock(return_value=True)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        mock_dyn_dev().configure.assert_called_once()
        assert mock_dyn_dev().configure.mock_calls[0][1][0]["port"] == port1
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={dynalite.CONF_HOST: host, dynalite.CONF_PORT: port2},
        )
        await hass.async_block_till_done()
        assert mock_dyn_dev().configure.call_count == 2
        assert mock_dyn_dev().configure.mock_calls[1][1][0]["port"] == port2
    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"


async def test_two_entries(hass, enable_custom_integrations):
    """Test when two different entries exist with different hosts."""
    host1 = "1.2.3.4"
    host2 = "5.6.7.8"
    MockConfigEntry(
        domain=DOMAIN, data={dynalite.CONF_HOST: host1}, version=2
    ).add_to_hass(hass)
    with patch(
        "custom_components.dynalite2.bridge.DynaliteDevices.async_setup",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={dynalite.CONF_HOST: host2},
        )
    assert result["type"] == "create_entry"
    assert result["result"].state == config_entries.ConfigEntryState.LOADED


async def test_user_flow(hass, enable_custom_integrations):
    """Test the basic user initiated flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] is None

    host = "1.2.3.4"
    port = 724
    with patch(
        "homeassistant.components.dynalite.bridge.DynaliteDevices.async_setup",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {dynalite.CONF_HOST: host, dynalite.CONF_PORT: port},
        )

    assert result["type"] == "create_entry"
    assert result["title"] == host
    assert result["data"] == {dynalite.CONF_HOST: host, dynalite.CONF_PORT: port}


async def test_user_flow_cannot_connect(hass, enable_custom_integrations):
    """Test user flow with a connection error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] is None

    host = "1.2.3.4"
    port = 724
    with patch(
        "homeassistant.components.dynalite.bridge.DynaliteDevices.async_setup",
        return_value=False,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {dynalite.CONF_HOST: host, dynalite.CONF_PORT: port},
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_generic_exception(hass, enable_custom_integrations):
    """Test user flow with a generic exception."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] is None

    host = "1.2.3.4"
    port = 724
    with patch(
        "homeassistant.components.dynalite.bridge.DynaliteDevices.async_setup",
        side_effect=Exception,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {dynalite.CONF_HOST: host, dynalite.CONF_PORT: port},
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "unknown"}
