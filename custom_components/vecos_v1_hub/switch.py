from __future__ import annotations

from typing import Optional

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VecosV1HubCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: VecosV1HubCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VecosUsbSwitch(coordinator, entry)])


class VecosUsbSwitch(CoordinatorEntity, RestoreEntity, SwitchEntity):
    def __init__(self, coordinator: VecosV1HubCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Vecos V1 Hub ({entry.data[CONF_HOST]})",
            manufacturer="Vecos",
            model="V1 Hub",
        )
        self._attr_is_on: Optional[bool] = None
        coordinator.register_usb_switch_entity(self)

    @property
    def name(self) -> str:
        return "Vecos Hub USB/Lighting"

    @property
    def unique_id(self) -> str:
        return f"{self.entry.entry_id}_usb_power"

    @property
    def is_on(self) -> Optional[bool]:
        data = self.coordinator.data
        if not data:
            return self._attr_is_on
        return bool(data.get("usb_power"))

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None:
            return
        if last_state.state == "on":
            self._attr_is_on = True
        elif last_state.state == "off":
            self._attr_is_on = False

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_set_usb(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_set_usb(False)
        await self.coordinator.async_request_refresh()

    async def async_update(self) -> None:
        await self.coordinator.async_request_refresh()
