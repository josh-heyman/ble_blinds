from homeassistant.components.cover import CoverEntity, CoverEntityFeature, ATTR_POSITION
from . import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BleBlindsCover(hub)])

class BleBlindsCover(CoverEntity):
    def __init__(self, hub):
        self._hub = hub
        self._attr_name = hub.name
        self._attr_unique_id = f"cover_{hub.mac.replace(':', '')}"
        self._attr_supported_features = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE |
            CoverEntityFeature.SET_POSITION | CoverEntityFeature.STOP
        )

    @property
    def device_info(self):
        """Links this entity directly to the primary Device."""
        return {
            "identifiers": {(DOMAIN, self._hub.mac)},
            "name": self._hub.name,
            "manufacturer": "DIY",
            "model": "BLE Smart Blinds",
        }

    @property
    def current_cover_position(self):
        return self._hub.current_position

    @property
    def is_closed(self) -> bool:
        return self._hub.current_position == 0

    async def async_added_to_hass(self):
        """Subscribe to updates when the hub receives Bluetooth data."""
        self._hub.position_callbacks.append(self._update_state)

    def _update_state(self, position):
        if self.hass:
            self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)

    async def async_open_cover(self, **kwargs):
        await self._hub.send_command(bytearray())

    async def async_close_cover(self, **kwargs):
        await self._hub.send_command(bytearray())

    async def async_set_cover_position(self, **kwargs):
        position = kwargs.get(ATTR_POSITION)
        if position is not None:
            await self._hub.send_command(bytearray([position]))

    async def async_stop_cover(self, **kwargs):
        await self._hub.send_command(bytearray())
