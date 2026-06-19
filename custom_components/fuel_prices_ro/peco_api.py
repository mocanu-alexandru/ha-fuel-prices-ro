"""Fallback fuel-price source: peco-online.ro.

This is an *independent* crawl (different operator from the primary Consiliul
Concurenței source), used ONLY when the primary monitorulpreturilor.info source
fails — e.g. the multi-week TLS-chain outage in mid-2026. peco-online.ro is a
commercial aggregator with no public/documented API; we POST the exact form its
own website uses and parse the server-rendered ``rezultate`` JSON array.

Because this is undocumented scraping, it is treated as inherently fragile: any
parse/HTTP failure yields an empty list (logged at debug), never an exception.
Numbers may differ slightly from the primary source (different station set and
crawl), so fallback items are tagged ``source="fallback"``.
"""
from __future__ import annotations

import json
import logging
import re

import aiohttp

from .api import FuelPriceItem
from .const import (
    BRANDS,
    DEFAULT_UATS,
    FUEL_CATEGORIES,
    HTTP_TIMEOUT_SECONDS,
    PECO_BRAND_MAP,
    PECO_FUEL_MAP,
    URL_PECO_FALLBACK,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

# `    var rezultate = JSON.parse('<json>');` — match a properly-escaped JS
# single-quoted string so an apostrophe in the payload can't truncate us.
_REZULTATE_RE = re.compile(
    r"var rezultate = JSON\.parse\('((?:[^'\\]|\\.)*)'\);", re.S
)


class PecoFallbackClient:
    """Best-effort fallback over peco-online.ro's server-rendered results."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)
        self._headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,*/*",
            "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
        }

    async def fetch_prices(
        self,
        uat_id: str,
        catprod_id: str,
        brand_ids: list[str],
    ) -> list[FuelPriceItem]:
        """Mirror the primary client's signature for one fuel category.

        Returns ``[]`` (never raises) if the city isn't mappable, the fuel is
        unknown to peco, or anything about the request/parse goes wrong.
        """
        city = DEFAULT_UATS.get(uat_id)
        carburant = PECO_FUEL_MAP.get(catprod_id)
        if not city or not carburant:
            return []

        retele = [
            PECO_BRAND_MAP[b] for b in brand_ids if b in PECO_BRAND_MAP
        ]
        if not retele:
            return []

        form: list[tuple[str, str]] = [
            ("carburant", carburant),
            ("locatie", "Oras"),
            ("nume_locatie", city),
            *[("retele[]", r) for r in retele],
        ]

        try:
            async with self._session.post(
                URL_PECO_FALLBACK,
                data=form,
                headers=self._headers,
                timeout=self._timeout,
            ) as resp:
                resp.raise_for_status()
                body = await resp.text()
        except aiohttp.ClientError as err:
            _LOGGER.debug("peco fallback HTTP failure: %s", err)
            return []

        return self._parse(body, uat_id, catprod_id)

    @staticmethod
    def _parse(
        body: str, uat_id: str, catprod_id: str
    ) -> list[FuelPriceItem]:
        match = _REZULTATE_RE.search(body)
        if not match or match.group(1) == "null":
            return []
        # Unescape the JS string literal back to raw JSON.
        raw = match.group(1).replace("\\'", "'").replace("\\\\", "\\")
        try:
            rows = json.loads(raw)
        except json.JSONDecodeError as err:
            _LOGGER.debug("peco fallback JSON parse failed: %s", err)
            return []

        fuel_name = FUEL_CATEGORIES.get(catprod_id, "")
        items: list[FuelPriceItem] = []
        for row in rows:
            # row = [brand, lat, lon, city, address, price]
            try:
                peco_brand = str(row[0])
                price = float(row[5])
                address = str(row[4])
            except (IndexError, ValueError, TypeError):
                continue

            brand_id = peco_brand.upper()
            if brand_id not in BRANDS:
                continue  # unknown/independent station — skip

            items.append(FuelPriceItem(
                uat_id=uat_id,
                station_id=address or "unknown",
                brand_id=brand_id,
                brand_name=BRANDS[brand_id],
                catprod_id=catprod_id,
                catprod_name=fuel_name,
                product_name="",
                price=price,
                distance_km=None,
                source="fallback",
            ))
        return items
