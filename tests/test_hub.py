from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from custom_components.vecos_v1_hub.coordinator import VecosV1HubCoordinator
from custom_components.vecos_v1_hub.hub import VecosV1HubClient


def test_get_status_sends_provided_bytes() -> None:
    client = VecosV1HubClient("127.0.0.1", 5000)

    with patch("builtins.print") as mock_print, patch.object(
        client, "_send_command", return_value=b"\x00" * 9
    ) as mock_send:
        client._get_status_sync(0x80, 0x80, 0x02)

    assert mock_send.call_args_list[-1].args == (0x80, 0x80, 0x02)
    mock_print.assert_called_once_with("Vecos TX: FF 00 80 00 00 00 00 80 00 02")


def test_coordinator_collects_command_bytes_from_entities() -> None:
    hass = SimpleNamespace()
    coordinator = VecosV1HubCoordinator(hass, AsyncMock(), "test-entry")

    coordinator.register_lock_entity(1, SimpleNamespace(is_locked=False))
    coordinator.register_lock_entity(2, SimpleNamespace(is_locked=True))
    coordinator.register_usb_switch_entity(SimpleNamespace(is_on=True))

    assert coordinator._command_bytes_from_entities() == (0x80, 0x00, 0x02)


def test_coordinator_collects_overrides_for_commands() -> None:
    hass = SimpleNamespace()
    coordinator = VecosV1HubCoordinator(hass, AsyncMock(), "test-entry")

    coordinator.register_lock_entity(1, SimpleNamespace(is_locked=False))
    coordinator.register_lock_entity(2, SimpleNamespace(is_locked=True))
    coordinator.register_usb_switch_entity(SimpleNamespace(is_on=False))

    assert coordinator._command_bytes_from_entities(lock_overrides={1: 0}) == (
        0x00,
        0x00,
        0x00,
    )