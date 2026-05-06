"""Config + options flows for Romanian Fuel Prices."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import FuelPricesApiError, FuelPricesClient
from .const import (
    BRANDS,
    CONF_BRANDS,
    CONF_FUELS,
    CONF_SCAN_INTERVAL,
    CONF_UAT_ID,
    CONF_UAT_NAME,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DEFAULT_UATS,
    DOMAIN,
    FUEL_CATEGORIES,
)

_LOGGER = logging.getLogger(__name__)

# Reusable selector configs ---------------------------------------------------
_BRAND_OPTIONS = [
    selector.SelectOptionDict(value=bid, label=bname)
    for bid, bname in BRANDS.items()
]
_FUEL_OPTIONS = [
    selector.SelectOptionDict(value=fid, label=fname)
    for fid, fname in FUEL_CATEGORIES.items()
]


def _selection_schema(
    default_brands: list[str], default_fuels: list[str], default_hours: int,
) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_BRANDS, default=default_brands):
            selector.SelectSelector(selector.SelectSelectorConfig(
                options=_BRAND_OPTIONS,
                multiple=True,
                mode=selector.SelectSelectorMode.LIST,
            )),
        vol.Required(CONF_FUELS, default=default_fuels):
            selector.SelectSelector(selector.SelectSelectorConfig(
                options=_FUEL_OPTIONS,
                multiple=True,
                mode=selector.SelectSelectorMode.LIST,
            )),
        vol.Optional(CONF_SCAN_INTERVAL, default=default_hours):
            selector.NumberSelector(selector.NumberSelectorConfig(
                min=1, max=24, step=1,
                mode=selector.NumberSelectorMode.SLIDER,
                unit_of_measurement="h",
            )),
    })


# ---------------------------------------------------------------------------
# Config flow (initial setup)
# ---------------------------------------------------------------------------
class FuelPricesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Two-step wizard: 1) pick city, 2) pick brands + fuels + interval."""

    VERSION = 1

    def __init__(self) -> None:
        self._uats: dict[str, str] = {}
        self._uat_id: str | None = None
        self._uat_name: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Step 1: pick a city. Tries live UAT list, falls back to bundled."""
        if not self._uats:
            self._uats = await self._load_uats()

        if user_input is not None:
            self._uat_id = user_input[CONF_UAT_ID]
            self._uat_name = self._uats.get(self._uat_id, self._uat_id)

            await self.async_set_unique_id(f"{DOMAIN}_{self._uat_id}")
            self._abort_if_unique_id_configured()

            return await self.async_step_selection()

        options = [
            selector.SelectOptionDict(value=uat_id, label=uat_name)
            for uat_id, uat_name in sorted(
                self._uats.items(), key=lambda x: x[1]
            )
        ]
        schema = vol.Schema({
            vol.Required(CONF_UAT_ID): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        })
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_selection(
        self, user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Step 2: brands + fuels + scan interval."""
        if user_input is not None:
            return self.async_create_entry(
                title=f"Fuel Prices — {self._uat_name}",
                data={
                    CONF_UAT_ID: self._uat_id,
                    CONF_UAT_NAME: self._uat_name,
                    CONF_BRANDS: user_input[CONF_BRANDS],
                    CONF_FUELS: user_input[CONF_FUELS],
                    CONF_SCAN_INTERVAL: int(user_input.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS
                    )),
                },
            )

        return self.async_show_form(
            step_id="selection",
            data_schema=_selection_schema(
                default_brands=list(BRANDS.keys()),
                default_fuels=list(FUEL_CATEGORIES.keys()),
                default_hours=DEFAULT_SCAN_INTERVAL_HOURS,
            ),
            description_placeholders={"uat_name": self._uat_name or ""},
        )

    async def _load_uats(self) -> dict[str, str]:
        """Try live API; fall back to bundled DEFAULT_UATS."""
        try:
            client = FuelPricesClient(async_get_clientsession(self.hass))
            live = await client.fetch_uat_list()
            if live:
                return {u["id"]: u["name"] for u in live}
        except FuelPricesApiError as err:
            _LOGGER.warning(
                "Live UAT fetch failed (%s) — falling back to defaults", err,
            )
        return dict(DEFAULT_UATS)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return FuelPricesOptionsFlow(config_entry)


# ---------------------------------------------------------------------------
# Options flow (edit brands / fuels / interval after setup)
# ---------------------------------------------------------------------------
class FuelPricesOptionsFlow(config_entries.OptionsFlow):
    """Allow editing the entry's selections without re-adding it."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        # Don't store entry directly — use config_entry property in newer HA
        self._entry_id = entry.entry_id

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data={
                CONF_BRANDS: user_input[CONF_BRANDS],
                CONF_FUELS: user_input[CONF_FUELS],
                CONF_SCAN_INTERVAL: int(user_input.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS
                )),
            })

        entry = self.hass.config_entries.async_get_entry(self._entry_id)
        if entry is None:
            return self.async_abort(reason="unknown_entry")

        merged = {**entry.data, **entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=_selection_schema(
                default_brands=list(merged.get(CONF_BRANDS, BRANDS)),
                default_fuels=list(merged.get(CONF_FUELS, FUEL_CATEGORIES)),
                default_hours=int(merged.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_HOURS,
                )),
            ),
        )
