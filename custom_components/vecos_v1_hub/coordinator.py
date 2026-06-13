from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, Dict, Optional, Tuple

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .hub import VecosV1HubClient


class VecosV1HubCoordinator(DataUpdateCoordinator[dict[str, object]]):
    def __init__(self, hass: HomeAssistant, client: VecosV1HubClient, entry_id: str) -> None:
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.entry_id = entry_id
        self._lock_entities: dict[int, Any] = {}
        self._usb_switch_entity: Any | None = None
        self._last_command_bytes = (0, 0, 0)

    def register_lock_entity(self, lock_id: int, entity: Any) -> None:
        self._lock_entities[lock_id] = entity

    def register_usb_switch_entity(self, entity: Any) -> None:
        self._usb_switch_entity = entity

    def _command_bytes_from_entities(
        self,
        lock_overrides: Optional[Dict[int, int]] = None,
        usb_override: Optional[bool] = None,
    ) -> Tuple[int, int, int]:
        lock_overrides = lock_overrides or {}
        locks_1_8 = 0
        locks_9_16 = 0

        for lock_id, entity in self._lock_entities.items():
            if lock_id in lock_overrides:
                bit = lock_overrides[lock_id]
            else:
                is_locked = getattr(entity, "is_locked", None)
                if is_locked is None:
                    continue
                bit = 0 if is_locked else 1
            if 1 <= lock_id <= 8:
                locks_1_8 |= bit << (8 - lock_id)
            elif 9 <= lock_id <= 16:
                locks_9_16 |= bit << (16 - lock_id)

        lighting_usb = 0
        if usb_override is not None:
            lighting_usb = 0x02 if usb_override else 0x00
        elif self._usb_switch_entity is not None:
            is_on = getattr(self._usb_switch_entity, "is_on", None)
            if is_on is not None:
                lighting_usb = 0x02 if is_on else 0x00

        if not self._lock_entities and self.data:
            door_states = self.data.get("door_states")
            if isinstance(door_states, dict):
                for lock_id, state in door_states.items():
                    bit = int(bool(state))
                    if 1 <= lock_id <= 8:
                        locks_1_8 |= bit << (8 - lock_id)
                    elif 9 <= lock_id <= 16:
                        locks_9_16 |= bit << (16 - lock_id)
            usb_power = self.data.get("usb_power")
            if usb_power is not None:
                lighting_usb = 0x02 if usb_power else 0x00

        return locks_1_8, locks_9_16, lighting_usb

    def _update_optimistic_lock_state(self, lock_ids: list[int], state: int) -> None:
        locked = not bool(state)
        for lock_id in lock_ids:
            entity = self._lock_entities.get(lock_id)
            if entity is None:
                continue
            setattr(entity, "_attr_is_locked", locked)
            entity.async_write_ha_state()

    async def async_set_lock_state(self, lock_id: int, state: int) -> None:
        await self.async_set_lock_states([lock_id], state)

    async def async_set_lock_states(self, lock_ids: list[int], state: int) -> None:
        locks_1_8, locks_9_16, lighting_usb = self._command_bytes_from_entities(
            lock_overrides={lock_id: state for lock_id in lock_ids}
        )
        await self.client.send_command(locks_1_8, locks_9_16, lighting_usb)
        self._last_command_bytes = (locks_1_8, locks_9_16, lighting_usb)
        self._update_optimistic_lock_state(lock_ids, state)

    async def async_set_usb(self, on: bool) -> None:
        locks_1_8, locks_9_16, lighting_usb = self._command_bytes_from_entities(
            usb_override=on
        )
        await self.client.send_command(locks_1_8, locks_9_16, lighting_usb)
        if self._usb_switch_entity is not None:
            setattr(self._usb_switch_entity, "_attr_is_on", on)
            self._usb_switch_entity.async_write_ha_state()
        self._last_command_bytes = (locks_1_8, locks_9_16, lighting_usb)

    async def _async_update_data(self) -> dict[str, object]:
        data: Optional[dict[str, object]] = await self.client.get_status(
            *self._last_command_bytes
        )
        if data is None:
            raise UpdateFailed("No response from hub")
        return data
