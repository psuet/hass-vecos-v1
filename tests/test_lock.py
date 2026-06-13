from __future__ import annotations

from typing import Optional
from unittest.mock import AsyncMock, call

from homeassistant.const import CONF_PORT
from tests.common import MockConfigEntry

from custom_components.vecos_v1_hub.const import DOMAIN
from custom_components.vecos_v1_hub.coordinator import VecosV1HubCoordinator
from custom_components.vecos_v1_hub.lock import VecosLockEntity, async_setup_entry


def _create_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={"host": "127.0.0.1", CONF_PORT: 5000},
        entry_id="test-entry",
    )


def _create_coordinator(
    hass, data: Optional[dict] = None
) -> VecosV1HubCoordinator:
    client = AsyncMock()
    client.get_status = AsyncMock(return_value=data)
    coordinator = VecosV1HubCoordinator(hass, client, "test-entry")
    coordinator.data = data
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


async def test_async_setup_entry_adds_lock_entities(hass):
    entry = _create_entry()
    coordinator = _create_coordinator(hass, {"door_states": {}, "connection_states": {}})
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    entities = []

    def async_add_entities(new_entities):
        entities.extend(new_entities)

    await async_setup_entry(hass, entry, async_add_entities)

    assert len(entities) == 16
    assert isinstance(entities[0], VecosLockEntity)
    assert entities[0].unique_id == "test-entry_lock_1"
    assert entities[-1].unique_id == "test-entry_lock_16"


async def test_lock_entity_state_reflects_coordinator_data(hass):
    entry = _create_entry()
    coordinator = _create_coordinator(
        hass,
        {
            "door_states": {1: 1, 2: 0},
            "connection_states": {},
            "usb_power": 0,
            "usb_feedback": 0,
        },
    )

    locked = VecosLockEntity(coordinator, entry, 1)
    unlocked = VecosLockEntity(coordinator, entry, 2)

    assert locked.is_locked is True
    assert unlocked.is_locked is False


async def test_lock_entity_defaults_to_locked_without_data(hass):
    entry = _create_entry()
    coordinator = _create_coordinator(hass, None)

    entity = VecosLockEntity(coordinator, entry, 1)

    assert entity.is_locked is True


async def test_lock_entity_calls_client_and_refresh_on_lock_and_unlock(hass):
    entry = _create_entry()
    coordinator = _create_coordinator(hass, {"door_states": {1: 1}})
    coordinator.async_set_lock_state = AsyncMock()

    entity = VecosLockEntity(coordinator, entry, 1)

    await entity.async_unlock()
    coordinator.async_set_lock_state.assert_awaited_once_with(1, 1)
    coordinator.async_request_refresh.assert_awaited_once()

    coordinator.async_set_lock_state.reset_mock()
    coordinator.async_request_refresh.reset_mock()

    await entity.async_lock()
    coordinator.async_set_lock_state.assert_awaited_once_with(1, 0)
    coordinator.async_request_refresh.assert_awaited_once()


async def test_lock_entity_sync_wrappers_delegate_to_async(hass):
    entry = _create_entry()
    coordinator = _create_coordinator(hass, {"door_states": {1: 1}})
    coordinator.async_set_lock_state = AsyncMock()

    entity = VecosLockEntity(coordinator, entry, 1)

    entity.lock()
    entity.unlock()
    await entity.async_open()

    await hass.async_block_till_done()

    assert coordinator.async_set_lock_state.await_args_list == [
        call(1, 0),
        call(1, 1),
        call(1, 1),
    ]
    assert coordinator.async_request_refresh.await_count == 3


async def test_lock_entity_keeps_optimistic_state_when_coordinator_is_stale(hass):
    entry = _create_entry()
    coordinator = _create_coordinator(hass, {"door_states": {1: 0}})

    entity = VecosLockEntity(coordinator, entry, 1)

    await entity.async_lock()

    assert entity.is_locked is True