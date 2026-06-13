import asyncio
import socket
from typing import Dict, Optional

class VecosV1HubClient:
    def __init__(self, host: str, port: int, timeout: float = 2.0) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout

    async def get_status(
        self, locks_1_8: int, locks_9_16: int, lighting_usb: int
    ) -> Optional[Dict[str, object]]:
        return await asyncio.to_thread(
            self._get_status_sync, locks_1_8, locks_9_16, lighting_usb
        )

    async def send_command(
        self, locks_1_8: int, locks_9_16: int, lighting_usb: int
    ) -> None:
        await asyncio.to_thread(self._send_command, locks_1_8, locks_9_16, lighting_usb)

    def _get_status_sync(
        self, locks_1_8: int, locks_9_16: int, lighting_usb: int
    ) -> Optional[Dict[str, object]]:
        response = self._send_command(locks_1_8, locks_9_16, lighting_usb)
        return self._parse_response(response)

    def _send_command(self, locks_1_8: int, locks_9_16: int, lighting_usb: int) -> bytes:
        payload = bytes(
            [
                0xFF,
                0x00,
                locks_1_8,
                0x00,
                0x00,
                0x00,
                0x00,
                locks_9_16,
                0x00,
                lighting_usb,
            ]
        )
        with socket.create_connection((self._host, self._port), self._timeout) as sock:
            sock.settimeout(self._timeout)
            sock.sendall(payload)
            return sock.recv(9)

    def _parse_response(self, response: bytes) -> Optional[Dict[str, object]]:
        if len(response) != 9:
            return None

        doors_8_1 = response[0]
        conn_8_1 = response[2]
        doors_16_9 = response[5]
        conn_16_9 = response[7]
        usb_light = response[8]

        door_states: Dict[int, int] = {}
        for index in range(8):
            door_states[index + 1] = (doors_8_1 >> index) & 1
        for index in range(8):
            door_states[index + 9] = (doors_16_9 >> index) & 1

        connection_states: Dict[int, int] = {}
        for index in range(8):
            connection_states[index + 1] = (conn_8_1 >> index) & 1
        for index in range(8):
            connection_states[index + 9] = (conn_16_9 >> index) & 1

        usb_power = (usb_light >> 1) & 1
        usb_feedback = usb_light & 1

        return {
            "door_states": door_states,
            "connection_states": connection_states,
            "usb_power": usb_power,
            "usb_feedback": usb_feedback,
        }
