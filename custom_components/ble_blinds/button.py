from homeassistant.components.button import ButtonEntity
from . import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        BleBlindsLimitButton(hub, "Set Top Limit", 251),
        BleBlindsLimitButton(hub, "Set Bottom Limit", 252),
    ])

class BleBlindsLimitButton(ButtonEntity):
    def __init__(self, hub, name_suffix, command_byte):
        self._hub = hub
        self._command_byte = command_byte
        self._attr_name = f"{hub.name} {name_suffix}"
        self._attr_unique_id = f"button_{name_suffix.lower().replace(' ', '_')}_{hub.mac.replace(':', '')}"

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._hub.mac)}}

    async def async_press(self) -> None:
        await self._hub.send_command(bytearray([self._command_byte]))
