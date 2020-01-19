"""Platform for water_heater integration."""
import logging
from datetime import timedelta
from typing import Optional

from homeassistant.components.water_heater import (
    # SUPPORT_AWAY_MODE,
    SUPPORT_OPERATION_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    WaterHeaterDevice,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PRECISION_TENTHS, PRECISION_WHOLE, TEMP_CELSIUS
from homeassistant.helpers.typing import HomeAssistantType
from pymelcloud import Ecodan

from .const import DOMAIN, TEMP_UNIT_LOOKUP

ENTITY_ID_FORMAT = DOMAIN + ".water_heater.{}"
SCAN_INTERVAL = timedelta(seconds=60)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigEntry, async_add_entities
):
    """Setup up MELCloud water_heater based on config_entry."""
    mel_devices = hass.data[DOMAIN].get(entry.entry_id)
    async_add_entities(
        [
            EcodanWaterHeater(mel_device)
            for mel_device in mel_devices
            if isinstance(mel_device.device, Ecodan)
        ],
        True,
    )


class EcodanWaterHeater(WaterHeaterDevice):
    """MELCloud water_heater device."""

    def __init__(self, device: Ecodan, name=None):
        """Initialize the water_heater."""
        self._api = device
        if name is None:
            name = device.name

        self._name = f"{name} Ecodan"

    @property
    def unique_id(self) -> Optional[str]:
        """Return a unique ID."""
        return f"{self._api.device.serial}-{self._api.device.mac}-water_heater"

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.

        False if entity pushes its state to HA.
        """
        return True

    async def async_update(self):
        """Update state from MELCloud."""
        await self._api.async_update()

    @property
    def device_info(self):
        """Return a device description for device registry."""
        return self._api.device_info

    @property
    def precision(self):
        """Return the precision of the system."""
        if self.hass.config.units.temperature_unit == TEMP_CELSIUS:
            return PRECISION_TENTHS
        return PRECISION_WHOLE

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_UNIT_LOOKUP.get(self._api.device.temp_unit, TEMP_CELSIUS)

    @property
    def current_operation(self):
        """Return current operation ie. eco, electric, performance, ..."""
        return "heat"

    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return ["heat"]

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._api.device.tank_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._api.device.target_tank_temperature

    @property
    def target_temperature_high(self):
        """Return the highbound target temperature we try to reach."""
        return None

    @property
    def target_temperature_low(self):
        """Return the lowbound target temperature we try to reach."""
        return None

    @property
    def is_away_mode_on(self):
        """Return true if away mode is on."""
        return None

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        raise NotImplementedError()

    async def async_set_operation_mode(self, operation_mode):
        """Set new target operation mode."""
        raise NotImplementedError()

    async def async_turn_away_mode_on(self):
        """Turn away mode on."""
        raise NotImplementedError()

    async def async_turn_away_mode_off(self):
        """Turn away mode off."""
        raise NotImplementedError()

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_OPERATION_MODE | SUPPORT_TARGET_TEMPERATURE

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._api.device.target_tank_temperature_min

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._api.device.target_tank_temperature_max
