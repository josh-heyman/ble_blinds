from homeassistant.components.number import NumberEntity
from . import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        BleBlindsConfigNumber(hub, "Motor Speed", 253, 100, 2000, 100),
        BleBlindsConfigNumber(hub, "Motor Acceleration", 254, 50, 1000, 50),
    ])

class BleBlindsConfigNumber(NumberEntity):
    def __init__(self, hub, label, prefix_byte, min_val, max_val, step_val):
        self._hub = hub
        self._prefix_byte = prefix_byte
        self._attr_name = f"{hub.name} {label}"
        self._attr_unique_id = f"number_{label.lower().replace(' ', '_')}_{hub.mac.replace(':', '')}"
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step_val
        self._attr_native_value = min_val  # Default starting value representation

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._hub.mac)}}

    async def async_set_native_value(self, value: float) -> None:
        """Fires when you adjust the slider."""
        self._attr_native_value = value
        # Send [Prefix Command Byte, Slider Integer Value]
        # Max out single byte transmission to 255 if needed, or split values if steps > 255
        int_value = int(value)
        
        # If your speed/accel values exceed 255, send them as high/low bytes:
        high_byte = (int_value >> 8) & 0xFF
        low_byte = int_value & 0xFF
        
        await self._hub.send_command(bytearray([self._prefix_byte, high_byte, low_byte]))
        self.async_write_ha_state()
