from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS, SERVICE_CLOSE_LOCKS, SERVICE_OPEN_LOCKS
from .coordinator import VecosV1HubCoordinator
from .hub import VecosV1HubClient


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})

    async def _handle_lock_service(call) -> None:
        entry_id = call.data["entry_id"]
        lock_ids = call.data["lock_ids"]
        coordinator = hass.data[DOMAIN].get(entry_id)
        if coordinator is None:
            return
        state = 1 if call.service == SERVICE_OPEN_LOCKS else 0
        await coordinator.async_set_lock_states(lock_ids, state)
        await coordinator.async_request_refresh()

    service_schema = vol.Schema(
        {
            vol.Required("entry_id"): str,
            vol.Required("lock_ids"): [vol.Coerce(int)],
        }
    )
    hass.services.async_register(
        DOMAIN, SERVICE_OPEN_LOCKS, _handle_lock_service, schema=service_schema
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CLOSE_LOCKS, _handle_lock_service, schema=service_schema
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    client = VecosV1HubClient(host, port)
    coordinator = VecosV1HubCoordinator(hass, client, entry.entry_id)

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator._last_command_bytes = coordinator._command_bytes_from_entities()
    await coordinator.async_config_entry_first_refresh()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
