import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    hub = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BleBlindsBatterySensor(hub)])

class BleBlindsBatterySensor(SensorEntity):
    def __init__(self, hub):
        self._hub = hub
        self._attr_name = f"{hub.name} Battery"
        self._attr_unique_id = f"sensor_battery_{hub.mac.replace(':', '')}"
        
        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_native_value = None

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self._hub.mac)}}

    async def async_added_to_hass(self):
        self._hub.battery_callbacks.append(self._update_state)

    def _update_state(self, battery_level):
        self._attr_native_value = battery_level
        if self.hass:
            self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)
