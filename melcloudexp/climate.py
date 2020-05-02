"""Platform for climate integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from pymelcloud import DEVICE_TYPE_ATA, DEVICE_TYPE_ATW, AtaDevice, AtwDevice
import pymelcloud.ata_device as ata
import pymelcloud.atw_device as atw
import voluptuous as vol

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    HVAC_MODE_COOL,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    SUPPORT_FAN_MODE,
    SUPPORT_SWING_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TEMP_CELSIUS
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform

from . import MelCloudDevice
from .const import (
    ATTR_STATUS,
    ATTR_VANE_HORIZONTAL,
    ATTR_VANE_HORIZONTAL_POSITIONS,
    ATTR_VANE_VERTICAL,
    ATTR_VANE_VERTICAL_POSITIONS,
    CONF_POSITION,
    DOMAIN,
    SERVICE_SET_VANE_HORIZONTAL,
    SERVICE_SET_VANE_VERTICAL,
)

SCAN_INTERVAL = timedelta(seconds=60)


ATA_HVAC_MODE_LOOKUP = {
    ata.OPERATION_MODE_HEAT: HVAC_MODE_HEAT,
    ata.OPERATION_MODE_DRY: HVAC_MODE_DRY,
    ata.OPERATION_MODE_COOL: HVAC_MODE_COOL,
    ata.OPERATION_MODE_FAN_ONLY: HVAC_MODE_FAN_ONLY,
    ata.OPERATION_MODE_HEAT_COOL: HVAC_MODE_HEAT_COOL,
}
ATA_HVAC_MODE_REVERSE_LOOKUP = {v: k for k, v in ATA_HVAC_MODE_LOOKUP.items()}

ATW_ZONE_FLOW_MODE_HEAT = "heat"
ATW_ZONE_FLOW_MODE_COOL = "cool"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up MelCloud device climate based on config_entry."""
    mel_devices = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AtaDeviceClimate(mel_device, mel_device.device)
            for mel_device in mel_devices[DEVICE_TYPE_ATA]
        ]
        + [
            AtwDeviceZoneThermostatClimate(mel_device, mel_device.device, zone)
            for mel_device in mel_devices[DEVICE_TYPE_ATW]
            for zone in mel_device.device.zones
        ]
        + [
            AtwDeviceZoneFlowClimate(
                mel_device, mel_device.device, zone, ATW_ZONE_FLOW_MODE_HEAT
            )
            for mel_device in mel_devices[DEVICE_TYPE_ATW]
            for zone in mel_device.device.zones
            if atw.ZONE_OPERATION_MODE_HEAT_FLOW in zone.operation_modes
        ]
        + [
            AtwDeviceZoneFlowClimate(
                mel_device, mel_device.device, zone, ATW_ZONE_FLOW_MODE_COOL
            )
            for mel_device in mel_devices[DEVICE_TYPE_ATW]
            for zone in mel_device.device.zones
            if atw.ZONE_OPERATION_MODE_COOL_FLOW in zone.operation_modes
        ],
        True,
    )

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_VANE_HORIZONTAL,
        {vol.Required(CONF_POSITION): cv.string},
        "async_set_vane_horizontal",
    )
    platform.async_register_entity_service(
        SERVICE_SET_VANE_VERTICAL,
        {vol.Required(CONF_POSITION): cv.string},
        "async_set_vane_vertical",
    )


class MelCloudClimate(ClimateEntity):
    """Base climate device."""

    def __init__(self, device: MelCloudDevice) -> None:
        """Initialize the climate."""
        self.api = device
        self._base_device = self.api.device
        self._name = device.name

    async def async_update(self):
        """Update state from MELCloud."""
        await self.api.async_update()

    @property
    def device_info(self):
        """Return a device description for device registry."""
        return self.api.device_info

    @property
    def target_temperature_step(self) -> float | None:
        """Return the supported step of target temperature."""
        return self._base_device.temperature_increment


class AtaDeviceClimate(MelCloudClimate):
    """Air-to-Air climate device."""

    def __init__(self, device: MelCloudDevice, ata_device: AtaDevice) -> None:
        """Initialize the climate."""
        super().__init__(device)
        self._device = ata_device

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return f"{self.api.device.serial}-{self.api.device.mac}"

    @property
    def name(self):
        """Return the display name of this entity."""
        return self._name

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the optional state attributes with device specific additions."""
        attr = {}

        vane_horizontal = self._device.vane_horizontal
        if vane_horizontal:
            attr.update(
                {
                    ATTR_VANE_HORIZONTAL: vane_horizontal,
                    ATTR_VANE_HORIZONTAL_POSITIONS: self._device.vane_horizontal_positions,
                }
            )

        vane_vertical = self._device.vane_vertical
        if vane_vertical:
            attr.update(
                {
                    ATTR_VANE_VERTICAL: vane_vertical,
                    ATTR_VANE_VERTICAL_POSITIONS: self._device.vane_vertical_positions,
                }
            )
        return attr

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        mode = self._device.operation_mode
        if not self._device.power or mode is None:
            return HVAC_MODE_OFF
        return ATA_HVAC_MODE_LOOKUP.get(mode)

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_OFF:
            await self._device.set({"power": False})
            return

        operation_mode = ATA_HVAC_MODE_REVERSE_LOOKUP.get(hvac_mode)
        if operation_mode is None:
            raise ValueError(f"Invalid hvac_mode [{hvac_mode}]")

        props = {"operation_mode": operation_mode}
        if self.hvac_mode == HVAC_MODE_OFF:
            props["power"] = True
        await self._device.set(props)

    @property
    def hvac_modes(self) -> list[str]:
        """Return the list of available hvac operation modes."""
        return [HVAC_MODE_OFF] + [
            ATA_HVAC_MODE_LOOKUP.get(mode) for mode in self._device.operation_modes
        ]

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._device.room_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._device.target_temperature

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        await self._device.set(
            {"target_temperature": kwargs.get("temperature", self.target_temperature)}
        )

    @property
    def fan_mode(self) -> str | None:
        """Return the fan setting."""
        return self._device.fan_speed

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        await self._device.set({"fan_speed": fan_mode})

    @property
    def fan_modes(self) -> list[str] | None:
        """Return the list of available fan modes."""
        return self._device.fan_speeds

    async def async_set_vane_horizontal(self, position: str) -> None:
        """Set horizontal vane position."""
        if position not in self._device.vane_horizontal_positions:
            raise ValueError(
                f"Invalid horizontal vane position {position}. Valid positions: [{self._device.vane_horizontal_positions}]."
            )
        await self._device.set({ata.PROPERTY_VANE_HORIZONTAL: position})

    async def async_set_vane_vertical(self, position: str) -> None:
        """Set vertical vane position."""
        if position not in self._device.vane_vertical_positions:
            raise ValueError(
                f"Invalid vertical vane position {position}. Valid positions: [{self._device.vane_vertical_positions}]."
            )
        await self._device.set({ata.PROPERTY_VANE_VERTICAL: position})

    @property
    def swing_mode(self) -> str | None:

        """Return vertical vane position or mode."""
        return self._device.vane_vertical

    async def async_set_swing_mode(self, swing_mode) -> None:
        """Set vertical vane position or mode."""
        await self.async_set_vane_vertical(swing_mode)

    @property
    def swing_modes(self) -> str | None:
        """Return a list of available vertical vane positions and modes."""
        return self._device.vane_vertical_positions

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_FAN_MODE | SUPPORT_TARGET_TEMPERATURE | SUPPORT_SWING_MODE

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self._device.set({"power": True})

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self._device.set({"power": False})

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        min_value = self._device.target_temperature_min
        if min_value is not None:
            return min_value

        return DEFAULT_MIN_TEMP

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        max_value = self._device.target_temperature_max
        if max_value is not None:
            return max_value

        return DEFAULT_MAX_TEMP


class AtwDeviceZoneClimate(MelCloudClimate):
    """Air-to-Water zone climate device."""

    def __init__(
        self, device: MelCloudDevice, atw_device: AtwDevice, atw_zone: atw.Zone
    ) -> None:
        """Initialize the climate."""
        super().__init__(device)
        self._device = atw_device
        self._zone = atw_zone

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the optional state attributes with device specific additions."""
        data = {
            ATTR_STATUS: self._zone.status,
        }
        return data

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE


class AtwDeviceZoneThermostatClimate(AtwDeviceZoneClimate):
    """Air-to-Water zone climate device."""

    def __init__(
        self, device: MelCloudDevice, atw_device: AtwDevice, atw_zone: atw.Zone
    ) -> None:
        """Initialize the climate."""
        super().__init__(device, atw_device, atw_zone)

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return f"{self.api.device.serial}-{self._zone.zone_index}"

    @property
    def name(self) -> str:
        """Return the display name of this entity."""
        return f"{self._name} {self._zone.name}"

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        op_mode = self._zone.operation_mode
        if not self._device.power or op_mode is None:
            return HVAC_MODE_OFF

        if op_mode == atw.ZONE_OPERATION_MODE_HEAT_THERMOSTAT:
            return HVAC_MODE_HEAT

        if op_mode == atw.ZONE_OPERATION_MODE_COOL_THERMOSTAT:
            return HVAC_MODE_COOL

        return HVAC_MODE_OFF

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_HEAT:
            operation_mode = atw.ZONE_OPERATION_MODE_HEAT_THERMOSTAT
        elif hvac_mode == HVAC_MODE_COOL:
            operation_mode = atw.ZONE_OPERATION_MODE_COOL_THERMOSTAT
        else:
            raise ValueError(f"Invalid hvac_mode '{hvac_mode}'")

        if self._zone.zone_index == 1:
            props = {atw.PROPERTY_ZONE_1_OPERATION_MODE: operation_mode}
        else:
            props = {atw.PROPERTY_ZONE_2_OPERATION_MODE: operation_mode}

        await self._device.set(props)

    @property
    def hvac_modes(self) -> list[str]:
        """Return the list of available hvac operation modes."""
        modes = []
        zone_modes = self._zone.operation_modes

        if atw.ZONE_OPERATION_MODE_HEAT_THERMOSTAT in zone_modes:
            modes.append(HVAC_MODE_HEAT)

        if atw.ZONE_OPERATION_MODE_COOL_FLOW in zone_modes:
            modes.append(HVAC_MODE_COOL)

        if self.hvac_mode == HVAC_MODE_OFF:
            modes.append(HVAC_MODE_OFF)

        return modes

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._zone.room_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        return self._zone.target_temperature

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        await self._zone.set_target_temperature(
            kwargs.get("temperature", self.target_temperature)
        )

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature.

        MELCloud API does not expose radiator zone temperature limits.
        """
        return 10

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature.

        MELCloud API does not expose radiator zone temperature limits.
        """
        return 30


class AtwDeviceZoneFlowClimate(AtwDeviceZoneClimate):
    """Air-to-Water zone climate device."""

    def __init__(
        self,
        device: MelCloudDevice,
        atw_device: AtwDevice,
        atw_zone: atw.Zone,
        flow_mode: str,
    ) -> None:
        """Initialize the climate."""
        super().__init__(device, atw_device, atw_zone)
        self._flow_mode = flow_mode

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        if self._flow_mode == ATW_ZONE_FLOW_MODE_HEAT:
            suffix = "heat-flow"
        else:
            suffix = "cool-flow"
        return f"{self.api.device.serial}-{self._zone.zone_index}-{suffix}"

    @property
    def name(self) -> str:
        """Return the display name of this entity."""
        if self._flow_mode == ATW_ZONE_FLOW_MODE_HEAT:
            suffix = "Heat Flow"
        else:
            suffix = "Cool Flow"
        return f"{self._name} {self._zone.name} {suffix}"

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""
        op_mode = self._zone.operation_mode
        if not self._device.power or op_mode is None:
            return HVAC_MODE_OFF

        if (
            self._flow_mode == ATW_ZONE_FLOW_MODE_HEAT
            and op_mode == atw.ZONE_OPERATION_MODE_HEAT_FLOW
        ):
            return HVAC_MODE_HEAT

        if (
            self._flow_mode == ATW_ZONE_FLOW_MODE_COOL
            and op_mode == atw.ZONE_OPERATION_MODE_COOL_FLOW
        ):
            return HVAC_MODE_COOL

        return HVAC_MODE_OFF

    async def async_set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        if self._flow_mode == ATW_ZONE_FLOW_MODE_HEAT and hvac_mode == HVAC_MODE_HEAT:
            operation_mode = atw.ZONE_OPERATION_MODE_HEAT_FLOW
        elif self._flow_mode == ATW_ZONE_FLOW_MODE_COOL and hvac_mode == HVAC_MODE_COOL:
            operation_mode = atw.ZONE_OPERATION_MODE_COOL_FLOW
        else:
            raise ValueError(f"Invalid hvac_mode '{hvac_mode}'")

        if self._zone.zone_index == 1:
            props = {atw.PROPERTY_ZONE_1_OPERATION_MODE: operation_mode}
        else:
            props = {atw.PROPERTY_ZONE_2_OPERATION_MODE: operation_mode}

        await self._device.set(props)

    @property
    def hvac_modes(self) -> list[str]:
        """Return the list of available hvac operation modes."""
        modes = []
        zone_modes = self._zone.operation_modes

        if (
            self._flow_mode == ATW_ZONE_FLOW_MODE_HEAT
            and atw.ZONE_OPERATION_MODE_HEAT_FLOW in zone_modes
        ):
            modes.append(HVAC_MODE_HEAT)

        if (
            self._flow_mode == ATW_ZONE_FLOW_MODE_COOL
            and atw.ZONE_OPERATION_MODE_COOL_FLOW in zone_modes
        ):
            modes.append(HVAC_MODE_COOL)

        if self.hvac_mode == HVAC_MODE_OFF:
            modes.append(HVAC_MODE_OFF)

        return modes

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._zone.flow_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        if self._flow_mode == ATW_ZONE_FLOW_MODE_HEAT:
            return self._zone.target_heat_flow_temperature

        return self._zone.target_cool_flow_temperature

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        if self._flow_mode == ATW_ZONE_FLOW_MODE_HEAT:
            await self._zone.set_target_heat_flow_temperature(
                kwargs.get("temperature", self.target_temperature)
            )
        else:
            await self._zone.set_target_cool_flow_temperature(
                kwargs.get("temperature", self.target_temperature)
            )

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature.

        MELCloud API does not expose radiator zone temperature limits.
        """
        if self._flow_mode == ATW_ZONE_FLOW_MODE_HEAT:
            return 25
        return 5

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature.

        MELCloud API does not expose radiator zone temperature limits.
        """
        if self._flow_mode == ATW_ZONE_FLOW_MODE_HEAT:
            return 60
        return 25
