import asyncio
import logging
from bleak import BleakClient
from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform, CONF_ADDRESS, CONF_NAME

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ble_blinds"
PLATFORMS = [Platform.COVER, Platform.BUTTON, Platform.NUMBER, Platform.SENSOR]

COMMAND_CHAR_UUID = "a06860ad-9bb1-46f8-b183-65396050c419"
STATE_CHAR_UUID = "33fcbe08-de24-448f-9b2b-91a0e68f81a7"
BATT_CHAR_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
CONFIG_CHAR_UUID = "bcf77398-84e1-4534-aac6-c0ac505cb688"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BLE Blinds device from a UI config entry."""
    mac = entry.data[CONF_ADDRESS]
    name = entry.data.get(CONF_NAME, "BLE Blinds")
    
    hub = BLEBlindsHub(hass, mac, name, entry.entry_id)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = hub
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Start the background connection loop instantly
    entry.async_create_background_task(hass, hub.background_loop(), "BLE Blinds Keepalive")
    
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
        
        # Config State
        self.current_speed = 4000
        self.current_accel = 2000
        
        # Callbacks
        self.position_callbacks = []
        self.battery_callbacks = []
        self.config_callbacks = []

    def _handle_disconnect(self, client):
        _LOGGER.warning(f"Disconnected from {self.mac}")
        self.client = None
        self.is_connecting = False

    def _notification_handler(self, sender, data):
        """Fires when the ESP32 pushes a new position."""
        self.current_position = data
        _LOGGER.debug(f"Hub received position update: {self.current_position}%")
        for callback in self.position_callbacks:
            callback()

    def _battery_notification_handler(self, sender, data):
        """Routes incoming battery data to the sensor."""
        battery_level = data
        _LOGGER.debug(f"Hub received battery update: {battery_level}%")
        for callback in self.battery_callbacks:
            callback(battery_level)

    def _config_notification_handler(self, sender, data):
        """Fires when the ESP32 pushes new config data."""
        self._parse_config_data(data)

    def _parse_config_data(self, data):
        """Helper to decode the 4-byte config payload."""
        if len(data) >= 4:
            self.current_speed = (data << 8) | data
            self.current_accel = (data << 8) | data
            _LOGGER.debug(f"Hub synced config: Speed={self.current_speed}, Accel={self.current_accel}")
            for callback in self.config_callbacks:
                callback()

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
                _LOGGER.debug(f"Device {self.mac} not found in scan cache.")
                return False

            self.client = BleakClient(ble_device, disconnected_callback=self._handle_disconnect)
            await self.client.connect(timeout=10.0)
            
            # Read current config immediately upon connection
            try:
                config_data = await self.client.read_gatt_char(CONFIG_CHAR_UUID)
                self._parse_config_data(config_data)
            except Exception as e:
                _LOGGER.warning(f"Could not read initial config from {self.mac}: {e}")

            # Subscribe to notifications
            await self.client.start_notify(STATE_CHAR_UUID, self._notification_handler)
            await self.client.start_notify(BATT_CHAR_UUID, self._battery_notification_handler)
            await self.client.start_notify(CONFIG_CHAR_UUID, self._config_notification_handler)
            
            _LOGGER.info(f"Connected to {self.mac} successfully.")
            return True
        except Exception as e:
            _LOGGER.debug(f"Failed connection to {self.mac}: {e}")
            self.client = None
            return False
        finally:
            self.is_connecting = False

    async def background_loop(self):
        """Runs forever to ensure we are always listening for state updates."""
        while True:
            if not self.client or not self.client.is_connected:
                await self.ensure_connected()
            await asyncio.sleep(10)

    async def send_command(self, payload: bytearray):
        """Helper to safely stream data through the shared connection."""
        if await self.ensure_connected():
            try:
                await self.client.write_gatt_char(COMMAND_CHAR_UUID, payload, response=True)
            except Exception as e:
                _LOGGER.error(f"Failed to write payload to {self.mac}: {e}")
