"""Data update coordinator for Romanian Fuel Prices."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import FuelPriceItem, FuelPricesApiError, FuelPricesClient
from .const import (
    CONF_BRANDS,
    CONF_FUELS,
    CONF_SCAN_INTERVAL,
    CONF_UAT_ID,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Coordinator data shape:
#   data[f"{brand_id}_{fuel_id}"] = {
#       "brand_id": str,        "brand_name": str,
#       "fuel_id":  str,        "fuel_name":  str,
#       "min_price": float,     "min_station_id": str,
#       "min_product_name": str,
#       "stations_count": int,
#       "all_stations": [
#           {"station_id": str, "product_name": str,
#            "price": float, "distance_km": float|None}, ...
#       ],
#   }


class FuelPricesCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Polls fuel prices for one UAT (city) every N hours."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry

        # Merge data + options (options override data after first edit)
        merged: dict[str, Any] = {**entry.data, **entry.options}
        self.uat_id: str = merged[CONF_UAT_ID]
        self.brand_ids: list[str] = list(merged[CONF_BRANDS])
        self.fuel_ids: list[str] = list(merged[CONF_FUELS])
        scan_hours: int = int(
            merged.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS)
        )

        self._client = FuelPricesClient(async_get_clientsession(hass))

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.uat_id}",
            update_interval=timedelta(hours=scan_hours),
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch all selected fuels for this UAT in parallel."""
        results = await asyncio.gather(
            *[
                self._client.fetch_prices(
                    self.uat_id, fuel_id, self.brand_ids
                )
                for fuel_id in self.fuel_ids
            ],
            return_exceptions=True,
        )

        all_items: list[FuelPriceItem] = []
        any_success = False
        for fuel_id, result in zip(self.fuel_ids, results, strict=True):
            if isinstance(result, BaseException):
                _LOGGER.warning(
                    "Fetch failed for fuel %s in UAT %s: %s",
                    fuel_id, self.uat_id, result,
                )
                continue
            any_success = True
            all_items.extend(result)

        if not any_success:
            raise UpdateFailed(
                f"All API calls failed for UAT {self.uat_id}"
            )

        return _aggregate_min_per_brand_fuel(all_items)


def _aggregate_min_per_brand_fuel(
    items: list[FuelPriceItem],
) -> dict[str, dict[str, Any]]:
    """Group raw items by (brand, fuel) -> min price + station list."""
    grouped: dict[tuple[str, str], list[FuelPriceItem]] = {}
    for item in items:
        grouped.setdefault((item.brand_id, item.catprod_id), []).append(item)

    out: dict[str, dict[str, Any]] = {}
    for (brand_id, fuel_id), group in grouped.items():
        cheapest = min(group, key=lambda x: x.price)
        out[f"{brand_id}_{fuel_id}"] = {
            "brand_id": brand_id,
            "brand_name": cheapest.brand_name,
            "fuel_id": fuel_id,
            "fuel_name": cheapest.catprod_name,
            "min_price": round(cheapest.price, 2),
            "min_station_id": cheapest.station_id,
            "min_product_name": cheapest.product_name,
            "stations_count": len(group),
            "all_stations": [
                {
                    "station_id": i.station_id,
                    "product_name": i.product_name,
                    "price": round(i.price, 2),
                    "distance_km": i.distance_km,
                }
                for i in sorted(group, key=lambda x: x.price)[:30]
            ],
        }
    return out
