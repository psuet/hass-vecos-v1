from __future__ import annotations

from typing import Optional

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NUMBER_OF_LOCKS
from .coordinator import VecosV1HubCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: VecosV1HubCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []
    for lock_id in range(1, entry.data[NUMBER_OF_LOCKS] + 1):
        entities.append(VecosDoorStateEntity(coordinator, entry, lock_id))
        entities.append(VecosConnectionStateEntity(coordinator, entry, lock_id))
    async_add_entities(entities)


class VecosBaseBinarySensor(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator: VecosV1HubCoordinator, entry: ConfigEntry, lock_id: int) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self.lock_id = lock_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Vecos V1 Hub ({entry.data[CONF_HOST]})",
            manufacturer="Vecos",
            model="V1 Hub",
        )

class VecosDoorStateEntity(VecosBaseBinarySensor):
    @property
    def name(self) -> str:
        return f"Vecos Lock {self.lock_id} Door"

    @property
    def unique_id(self) -> str:
        return f"{self.entry.entry_id}_door_{self.lock_id}"

    @property
    def is_on(self) -> Optional[bool]:
        data = self.coordinator.data
        if not data:
            return None
        return bool(data["door_states"].get(self.lock_id))


class VecosConnectionStateEntity(VecosBaseBinarySensor):
    @property
    def name(self) -> str:
        return f"Vecos Lock {self.lock_id} Connection"

    @property
    def unique_id(self) -> str:
        return f"{self.entry.entry_id}_connection_{self.lock_id}"

    @property
    def is_on(self) -> Optional[bool]:
        data = self.coordinator.data
        if not data:
            return None
        return bool(data["connection_states"].get(self.lock_id))
