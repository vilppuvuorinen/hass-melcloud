"""Constants for the MELCloud Climate integration."""
import pymelcloud

from homeassistant.const import (
	TEMP_CELSIUS,
	TEMP_FAHRENHEIT,
)
from homeassistant.components.climate.const import (
	HVAC_MODE_COOL,
	HVAC_MODE_HEAT,
	HVAC_MODE_HEAT_COOL,
	HVAC_MODE_DRY,
	HVAC_MODE_OFF,
	HVAC_MODE_FAN_ONLY,
	HVAC_MODES,
)
from homeassistant.const import CONF_ICON, CONF_NAME, CONF_TYPE

ATTR_TARGET_TEMPERATURE = "target_temperature"
ATTR_INSIDE_TEMPERATURE = "inside_temperature"
ATTR_OUTSIDE_TEMPERATURE = "outside_temperature"

DOMAIN = "melcloud"

HVAC_MODE_LOOKUP = {
	pymelcloud.OPERATION_MODE_HEAT: HVAC_MODE_HEAT,
	pymelcloud.OPERATION_MODE_DRY: HVAC_MODE_DRY,
	pymelcloud.OPERATION_MODE_COOL: HVAC_MODE_COOL,
	pymelcloud.OPERATION_MODE_FAN_ONLY: HVAC_MODE_FAN_ONLY,
	pymelcloud.OPERATION_MODE_HEAT_COOL: HVAC_MODE_HEAT_COOL,
}
HVAC_MODE_REVERSE_LOOKUP = {v: k for k, v in HVAC_MODE_LOOKUP.items()}

SENSOR_TYPE_TEMPERATURE = "temperature"

SENSOR_TYPES = {
    ATTR_INSIDE_TEMPERATURE: {
        CONF_NAME: "Inside Temperature",
        CONF_ICON: "mdi:thermometer",
        CONF_TYPE: SENSOR_TYPE_TEMPERATURE,
    },
    ATTR_OUTSIDE_TEMPERATURE: {
        CONF_NAME: "Outside Temperature",
        CONF_ICON: "mdi:thermometer",
        CONF_TYPE: SENSOR_TYPE_TEMPERATURE,
    },
}

TEMP_UNIT_LOOKUP = {
	pymelcloud.UNIT_TEMP_CELSIUS: TEMP_CELSIUS,
	pymelcloud.UNIT_TEMP_FAHRENHEIT: TEMP_FAHRENHEIT,
}
TEMP_UNIT_REVERSE_LOOKUP = {v: k for k, v in TEMP_UNIT_LOOKUP.items()}
