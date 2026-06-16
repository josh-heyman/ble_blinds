from homeassistant.components.number import NumberEntity
from . import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        BleBlindsConfigNumber(hub, "Motor Speed", 253, 100, 8000, 100, is_speed=True),
        BleBlindsConfigNumber(hub, "Motor Acceleration", 254, 50, 4000, 50, is_speed=False),
    ])

class BleBlindsConfigNumber(NumberEntity):
    def __init__(self, hub, label, prefix_byte, min_val, max_val, step_val, is_speed):
        self._hub = hub
        self._prefix_byte = prefix_byte
        self._is_speed = is_speed
        
        self._attr_name = f"{hub.name} {label}"
        self._attr_unique_id = f"number_{label.lower().replace(' ', '_')}_{hub.mac.replace(':', '')}"
        
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step_val

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._hub.mac)}}

    @property
    def native_value(self):
        if self._is_speed:
            return self._hub.current_speed
        return self._hub.current_accel

    async def async_added_to_hass(self):
        self._hub.config_callbacks.append(self._update_state)

    def _update_state(self):
        if self.hass:
            self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)

    async def async_set_native_value(self, value: float) -> None:
        int_value = int(value)
        high_byte = (int_value >> 8) & 0xFF
        low_byte = int_value & 0xFF
        await self._hub.send_command(bytearray([self._prefix_byte, high_byte, low_byte]))
