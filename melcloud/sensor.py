"""Support for MelCloud device sensors."""
import logging

from homeassistant.const import DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS
from homeassistant.helpers.entity import Entity
from homeassistant.util.unit_system import UnitSystem
from pymelcloud import Device, Ecodan, HeatPump

from .const import DOMAIN, TEMP_UNIT_LOOKUP

ATTR_MEASUREMENT = "measurement"
ATTR_ICON = "icon"
ATTR_UNIT_FN = "unit_fn"
ATTR_DEVICE_CLASS = "device_class"
ATTR_AVAILABLE = "available"
ATTR_VALUE_FN = "value_fn"

HEAT_PUMP_SENSORS = [
    {
        ATTR_MEASUREMENT: "Room Temperature",
        ATTR_ICON: "mdi:thermometer",
        ATTR_UNIT_FN: lambda x: TEMP_UNIT_LOOKUP.get(x.device.temp_unit, TEMP_CELSIUS),
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_AVAILABLE: lambda x: True,
        ATTR_VALUE_FN: lambda x: x.device.temperature,
    },
    {
        ATTR_MEASUREMENT: "Energy",
        ATTR_ICON: "mdi:factory",
        ATTR_UNIT_FN: lambda x: "kWh",
        ATTR_DEVICE_CLASS: None,
        ATTR_AVAILABLE: lambda x: True,
        ATTR_VALUE_FN: lambda x: x.device.total_energy_consumed,
    },
]

ECODAN_SENSORS = [
    {
        ATTR_MEASUREMENT: "Zone 1 Room Temperature",
        ATTR_ICON: "mdi:thermometer",
        ATTR_UNIT_FN: lambda x: TEMP_UNIT_LOOKUP.get(x.device.temp_unit, TEMP_CELSIUS),
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_AVAILABLE: lambda x: len(x.device.zones) >= 1,
        ATTR_VALUE_FN: lambda x: x.device.zones[0].room_temperature,
    },
    {
        ATTR_MEASUREMENT: "Zone 2 Room Temperature",
        ATTR_ICON: "mdi:thermometer",
        ATTR_UNIT_FN: lambda x: TEMP_UNIT_LOOKUP.get(x.device.temp_unit, TEMP_CELSIUS),
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_AVAILABLE: lambda x: len(x.device.zones) >= 2,
        ATTR_VALUE_FN: lambda x: x.device.zones[1].room_temperature,
    },
    {
        ATTR_MEASUREMENT: "Tank Water Temperature",
        ATTR_ICON: "mdi:thermometer",
        ATTR_UNIT_FN: lambda x: TEMP_UNIT_LOOKUP.get(x.device.temp_unit, TEMP_CELSIUS),
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_AVAILABLE: lambda x: True,
        ATTR_VALUE_FN: lambda x: x.device.tank_temperature,
    },
    {
        ATTR_MEASUREMENT: "Outside Temperature",
        ATTR_ICON: "mdi:thermometer",
        ATTR_UNIT_FN: lambda x: TEMP_UNIT_LOOKUP.get(x.device.temp_unit, TEMP_CELSIUS),
        ATTR_DEVICE_CLASS: DEVICE_CLASS_TEMPERATURE,
        ATTR_AVAILABLE: lambda x: True,
        ATTR_VALUE_FN: lambda x: x.device.outdoor_temperature,
    },
]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MELCloud device sensors based on config_entry."""
    mel_devices = hass.data[DOMAIN].get(entry.entry_id)
    async_add_entities(
        [
            MelCloudSensor(mel_device, definition, hass.config.units)
            for definition in HEAT_PUMP_SENSORS
            for mel_device in mel_devices
            if isinstance(mel_device.device, HeatPump)
        ]
        + [
            MelCloudSensor(mel_device, definition, hass.config.units)
            for definition in ECODAN_SENSORS
            for mel_device in mel_devices
            if isinstance(mel_device, Ecodan)
        ],
        True,
    )


class MelCloudSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, device: Device, definition, units: UnitSystem, name=None):
        """Initialize the sensor."""
        self._api = device
        if name is None:
            self._name_slug = device.name
        else:
            self._name_slug = name

        self._def = definition

    @property
    def unique_id(self):
        """Return a unique ID."""
        normalized = self._def[ATTR_MEASUREMENT].lower().replace(" ", "_")
        return f"{self._api.device.serial}-{self._api.device.mac}-{normalized}"

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return self._def[ATTR_ICON]

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name_slug} {self._def[ATTR_MEASUREMENT]}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._def[ATTR_VALUE_FN](self._api)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._def[ATTR_UNIT_FN](self._api)

    @property
    def device_class(self):
        """Return device class."""
        return self._def[ATTR_DEVICE_CLASS]

    async def async_update(self):
        """Retrieve latest state."""
        await self._api.async_update()

    @property
    def device_info(self):
        """Return a device description for device registry."""
        return self._api.device_info
