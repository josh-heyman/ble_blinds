import asyncio
import logging
from bleak import BleakClient
from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature,
    ATTR_POSITION,
)
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.const import CONF_ADDRESS, CONF_NAME

_LOGGER = logging.getLogger(__name__)

COMMAND_CHAR_UUID = "a06860ad-9bb1-46f8-b183-65396050c419"
STATE_CHAR_UUID = "33fcbe08-de24-448f-9b2b-91a0e68f81a7"


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the BLE Blinds cover from a UI config entry."""
    mac = entry.data[CONF_ADDRESS]
    name = entry.data.get(CONF_NAME, "BLE Blinds")
    async_add_entities([BleBlindsCover(mac, name)])


class BleBlindsCover(CoverEntity):
    """Representation of the BLE Blinds Cover."""

    def __init__(self, mac, name):
        self._mac = mac
        self._attr_name = name
        self._attr_unique_id = f"ble_blinds_{mac.replace(':', '')}"
        self._attr_current_cover_position = 50
        self._client = None
        self._is_connecting = False

        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.SET_POSITION
            | CoverEntityFeature.STOP
        )

    @property
    def is_closed(self) -> bool:
        return self._attr_current_cover_position == 0

    def _notification_handler(self, sender, data):
        """Handle incoming state updates from the ESP32."""
        new_position = data
        self._attr_current_cover_position = new_position
        _LOGGER.debug(f"Received new position: {new_position}%")
        self.schedule_update_ha_state()

    async def _ensure_connected(self):
        """Maintain a connection to the ESP32."""
        if self._client and self._client.is_connected:
            return True

        if self._is_connecting:
            await asyncio.sleep(1)
            return self._client and self._client.is_connected

        self._is_connecting = True
        try:
            # Grab the device directly from Home Assistant's scanner cache
            ble_device = async_ble_device_from_address(
                self.hass, self._mac, connectable=True
            )
            if not ble_device:
                _LOGGER.error(
                    f"Device {self._mac} not found in HA Bluetooth scan cache."
                )
                return False

            _LOGGER.info(f"Connecting to BLE Blinds at {self._mac}...")
            # Pass the device object instead of MAC for rock-solid stability
            self._client = BleakClient(ble_device)
            await self._client.connect()

            await self._client.start_notify(STATE_CHAR_UUID, self._notification_handler)
            _LOGGER.info("Connected and subscribed to notifications.")
            return True
        except Exception as e:
            _LOGGER.error(f"Failed to connect to {self._mac}: {e}")
            return False
        finally:
            self._is_connecting = False

    async def async_send_command(self, payload: bytearray):
        """Helper function to send commands."""
        if await self._ensure_connected():
            try:
                await self._client.write_gatt_char(COMMAND_CHAR_UUID, payload)
            except Exception as e:
                _LOGGER.error(f"Failed to write command to {self._mac}: {e}")

    # --- Home Assistant Native Actions ---

    async def async_open_cover(self, **kwargs):
        await self.async_send_command(bytearray())

    async def async_close_cover(self, **kwargs):
        await self.async_send_command(bytearray())

    async def async_set_cover_position(self, **kwargs):
        position = kwargs.get(ATTR_POSITION)
        if position is not None:
            await self.async_send_command(bytearray([position]))

    async def async_stop_cover(self, **kwargs):
        await self.async_send_command(bytearray())
