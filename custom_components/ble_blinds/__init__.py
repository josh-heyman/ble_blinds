import asyncio
import logging
from bleak import BleakClient
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform, CONF_ADDRESS, CONF_NAME

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ble_blinds"
PLATFORMS = [Platform.COVER, Platform.BUTTON, Platform.NUMBER]

COMMAND_CHAR_UUID = "a06860ad-9bb1-46f8-b183-65396050c419"
STATE_CHAR_UUID = "33fcbe08-de24-448f-9b2b-91a0e68f81a7"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BLE Blinds device from a UI config entry."""
    mac = entry.data[CONF_ADDRESS]
    name = entry.data.get(CONF_NAME, "BLE Blinds")
    
    # Initialize the central hub for this specific device
    hub = BLEBlindsHub(hass, mac, name, entry.entry_id)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

class BLEBlindsHub:
    """Thread-safe Connection Hub managing the single BLE connection."""

    def __init__(self, hass: HomeAssistant, mac: str, name: str, entry_id: str):
        self.hass = hass
        self.mac = mac
        self.name = name
        self.entry_id = entry_id
        self.client = None
        self.is_connecting = False
        self.current_position = 50
        self.position_callbacks = []

    def _handle_disconnect(self, client):
        _LOGGER.warning(f"Disconnected from {self.mac}")
        self.client = None
        self.is_connecting = False

    def _notification_handler(self, sender, data):
        """Fires when the ESP32 pushes a new position."""
        self.current_position = data
        _LOGGER.debug(f"Hub received position update: {self.current_position}%")
        
        # Notify any listening entities (like the cover) to refresh their state
        for callback in self.position_callbacks:
            callback(self.current_position)

    async def ensure_connected(self) -> bool:
        """Maintains the shared connection."""
        if self.client and self.client.is_connected:
            return True

        if self.is_connecting:
            await asyncio.sleep(1.5)
            return self.client and self.client.is_connected

        self.is_connecting = True
        try:
            ble_device = async_ble_device_from_address(self.hass, self.mac, connectable=True)
            if not ble_device:
                _LOGGER.error(f"Device {self.mac} not found in scan cache.")
                return False

            self.client = BleakClient(ble_device, disconnected_callback=self._handle_disconnect)
            await self.client.connect(timeout=10.0)
            
            await self.client.start_notify(STATE_CHAR_UUID, self._notification_handler)
            _LOGGER.info(f"Connected to {self.mac} successfully.")
            return True
        except Exception as e:
            _LOGGER.error(f"Failed connection to {self.mac}: {e}")
            self.client = None
            return False
        finally:
            self.is_connecting = False

    async def send_command(self, payload: bytearray):
        """Helper to safely stream data through the shared connection."""
        if await self.ensure_connected():
            try:
                await self.client.write_gatt_char(COMMAND_CHAR_UUID, payload, response=True)
            except Exception as e:
                _LOGGER.error(f"Failed to write payload to {self.mac}: {e}")
