from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

PLATFORMS = [Platform.COVER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BLE Blinds from a UI config entry."""
    hass.data.setdefault("ble_blinds", {})
    hass.data["ble_blinds"][entry.entry_id] = entry.data

    # Tell Home Assistant to load cover.py
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry when deleted from the UI."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data["ble_blinds"].pop(entry.entry_id)
    return unload_ok
