"""Diagnostics support for Fuel Prices Romania."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_BRANDS, CONF_FUELS, CONF_SCAN_INTERVAL, CONF_UAT_ID, DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    merged: dict[str, Any] = {**entry.data, **entry.options}

    return {
        "config": {
            "uat_id": merged.get(CONF_UAT_ID),
            "brands": merged.get(CONF_BRANDS),
            "fuels": merged.get(CONF_FUELS),
            "scan_interval_hours": merged.get(CONF_SCAN_INTERVAL),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "sensors_count": len(coordinator.data) if coordinator.data else 0,
            "sensor_keys": list(coordinator.data.keys()) if coordinator.data else [],
        },
    }
