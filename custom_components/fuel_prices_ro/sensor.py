"""Sensor entities for Romanian Fuel Prices."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    BRANDS,
    DEFAULT_UATS,
    DOMAIN,
    FUEL_CATEGORIES,
    FUEL_ICONS,
    FUEL_SLUGS,
)
from .coordinator import FuelPricesCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one sensor per (brand, fuel) selection."""
    coordinator: FuelPricesCoordinator = hass.data[DOMAIN][entry.entry_id]

    sensors = [
        FuelPriceSensor(coordinator, brand_id, fuel_id)
        for brand_id in coordinator.brand_ids
        for fuel_id in coordinator.fuel_ids
    ]
    async_add_entities(sensors)


class FuelPriceSensor(
    CoordinatorEntity[FuelPricesCoordinator], SensorEntity
):
    """Minimum price for one (brand, fuel) combo within a city."""

    _attr_attribution = ATTRIBUTION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "RON/L"
    _attr_suggested_display_precision = 2
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FuelPricesCoordinator,
        brand_id: str,
        fuel_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._brand_id = brand_id
        self._fuel_id = fuel_id
        self._key = f"{brand_id}_{fuel_id}"

        uat_id = coordinator.uat_id
        uat_name = DEFAULT_UATS.get(uat_id) or coordinator.entry.title
        brand_name = BRANDS.get(brand_id, brand_id.title())
        fuel_name = FUEL_CATEGORIES.get(fuel_id, f"Fuel {fuel_id}")
        fuel_slug = FUEL_SLUGS.get(fuel_id, fuel_id)

        self._attr_icon = FUEL_ICONS.get(fuel_id, "mdi:gas-station")

        self._attr_unique_id = (
            f"{DOMAIN}_{uat_id}_{brand_id.lower()}_{fuel_slug}"
        )
        self._attr_name = f"{brand_name} {fuel_name}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uat_id)},
            name=f"Fuel Prices {uat_name}",
            manufacturer="Consiliul Concurenței",
            model="Fuel price monitor",
            configuration_url="https://monitorulpreturilor.info/Home/Gas",
        )

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data or self._key not in data:
            return None
        return data[self._key].get("min_price")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not data or self._key not in data:
            return {}
        info = data[self._key]
        return {
            "brand_id": info.get("brand_id"),
            "brand_name": info.get("brand_name"),
            "fuel_id": info.get("fuel_id"),
            "fuel_name": info.get("fuel_name"),
            "uat_id": self.coordinator.uat_id,
            "min_station_id": info.get("min_station_id"),
            "min_product_name": info.get("min_product_name"),
            "stations_count": info.get("stations_count"),
            "all_stations": info.get("all_stations"),
        }

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        data = self.coordinator.data
        return bool(data and self._key in data)
