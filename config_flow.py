import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS, CONF_NAME

DOMAIN = "ble_blinds"


class BleBlindsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BLE Blinds."""

    VERSION = 1

    def __init__(self):
        """Initialize flow."""
        self._discovery_info = None

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak):
        """Triggered automatically when HA discovers the blinds."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovery_info = discovery_info
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(self, user_input=None):
        """Confirm discovery in the UI."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery_info.name or "BLE Blinds",
                data={
                    CONF_ADDRESS: self._discovery_info.address,
                    CONF_NAME: self._discovery_info.name or "BLE Blinds",
                },
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovery_info.name},
        )

    async def async_step_user(self, user_input=None):
        """Triggered when the user manually clicks 'Add Integration'."""
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_ADDRESS])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input.get(CONF_NAME, "BLE Blinds"),
                data=user_input,
            )

        # Scan for devices matching your specific UUID or Name
        discovered = async_discovered_service_info(self.hass)
        devices = {
            device.address: f"{device.name} ({device.address})"
            for device in discovered
            if "c52b8845-494d-4769-8e5f-6699e6b62b11" in device.service_uuids
            or device.name == "Josh's Blinds"
        }

        if not devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(devices),
                    vol.Optional(CONF_NAME, default="Living Room Blinds"): str,
                }
            ),
        )
