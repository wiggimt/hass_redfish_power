"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN
from .config_flow import RedfishPowerHub


def replace_invalid_entity_id_chars(entity_id: str) -> str:
    """Replace invalid characters with underscore."""
    return "".join(
        c if (c.isalpha() and c.islower()) or c == "_" else "" for c in entity_id
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> bool:
    hub = hass.data[DOMAIN][entry.entry_id]

    hostname = await hub.get_device_hostname()
    entity_id = f"{hostname}_power_consumption"

    async_add_entities(
        [
            RedfishPowerConsumptionSensor(
                "sensor." + replace_invalid_entity_id_chars(entity_id), hub
            )
        ],
        True,
    )
    return True


class RedfishPowerConsumptionSensor(SensorEntity):
    """Representation of a Sensor."""

    def __init__(self, entity_id: str, hub: RedfishPowerHub) -> None:
        self.entity_id = entity_id
        self.hub = hub
        self._attr_unique_id = f"{hub.host}_power_consumption"

    _attr_name = "Power Consumption"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._attr_native_value = await self.hub.get_power_consumption()
