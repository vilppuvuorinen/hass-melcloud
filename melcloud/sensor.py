"""Support for MelCloud device sensors."""
import logging

from pymelcloud import Device

from homeassistant.const import (
	CONF_ICON,
	CONF_NAME,
	CONF_TYPE,
	TEMP_CELSIUS,
)
from homeassistant.helpers.entity import Entity
from homeassistant.util.unit_system import UnitSystem

from .const import (
	ATTR_INSIDE_TEMPERATURE,
	ATTR_OUTSIDE_TEMPERATURE,
	DOMAIN,
	SENSOR_TYPE_TEMPERATURE,
	SENSOR_TYPES,
	TEMP_UNIT_LOOKUP
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
	"""Set up MelCloud device sensors based on config_entry."""
	entities = []
	mel_devices = hass.data[DOMAIN].get(entry.entry_id)
	for mel_device in mel_devices:
		entities.append(
			MelCloudSensor(
				mel_device,
				ATTR_INSIDE_TEMPERATURE,
				hass.config.units
			)
		)
		if False: #mel_device.device.support_outside_temperature:
			entities.append(
				MelCloudSensor(
					mel_device,
					ATTR_INSIDE_TEMPERATURE,
					hass.config.units
				)
			)

	async_add_entities(entities, True)

class MelCloudSensor(Entity):
	"""Representation of a Sensor."""

	def __init__(self, device: Device, monitored_state, units: UnitSystem, name=None) -> None:
		"""Initialize the sensor."""
		self._api = device
		self._sensor = SENSOR_TYPES.get(monitored_state)
		if name is None:
			name = device.name

		self._name = "{} {}".format(name, monitored_state.replace("_", " "))
		self._device_attribute = monitored_state

		if self._sensor[CONF_TYPE] == SENSOR_TYPE_TEMPERATURE:
			self._unit_of_measurement = units.temperature_unit

	@property
	def unique_id(self):
		"""Return a unique ID."""
		return f"{self._api.device.serial}-{self._api.device.mac}-{self._device_attribute}"

	@property
	def icon(self):
		"""Icon to use in the frontend, if any."""
		return self._sensor[CONF_ICON]

	@property
	def name(self):
		"""Return the name of the sensor."""
		return self._name

	@property
	def state(self):
		"""Return the state of the sensor."""
		if self._device_attribute == ATTR_INSIDE_TEMPERATURE:
			return self._api.device.temperature
		if self._device_attribute == ATTR_OUTSIDE_TEMPERATURE:
			raise NotImplementedError
		return None

	@property
	def unit_of_measurement(self):
		"""Return the unit of measurement."""
		return TEMP_UNIT_LOOKUP.get(self._api.device.temp_unit, TEMP_CELSIUS)

	async def async_update(self):
		"""Retrieve latest state."""
		await self._api.async_update()

	@property
	def device_info(self):
		"""Return a device description for device registry."""
		return self._api.device_info
