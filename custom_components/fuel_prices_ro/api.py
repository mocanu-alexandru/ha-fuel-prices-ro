"""Async client for monitorulpreturilor.info pmonsvc service."""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import aiohttp
from yarl import URL

from .const import (
    HTTP_TIMEOUT_SECONDS,
    URL_GAS_ITEMS,
    URL_GAS_NETWORKS,
    URL_UAT_LIST,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

# XML namespace used by the WCF data contract
XMLNS = "http://schemas.datacontract.org/2004/07/pmonsvc.Models.Protos"
NS = {"d": XMLNS}


@dataclass(frozen=True)
class FuelPriceItem:
    """A single price observation for one product at one station."""

    uat_id: str
    station_id: str
    brand_id: str
    brand_name: str
    catprod_id: str
    catprod_name: str
    product_name: str       # commercial variant, e.g. "BENZINA EVO 95"
    price: float            # RON/L
    distance_km: float | None


class FuelPricesApiError(Exception):
    """Raised on any API or parse failure."""


class FuelPricesClient:
    """Thin async client over the pmonsvc XML endpoints."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)
        self._headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/xml,*/*",
            "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
        }

    # -----------------------------------------------------------------
    # Prices
    # -----------------------------------------------------------------
    async def fetch_prices(
        self,
        uat_id: str,
        catprod_id: str,
        brand_ids: list[str],
    ) -> list[FuelPriceItem]:
        """Fetch all stations of selected brands for ONE fuel category.

        API quirk: ``CSVGasCatalogProductIds`` does NOT accept CSV
        (returns HTTP 500), but ``CSVGasNetworkIDS`` does.
        """
        url = URL(URL_GAS_ITEMS).with_query({
            "UatId": uat_id,
            "CSVGasCatalogProductIds": catprod_id,
            "CSVGasNetworkIDS": ",".join(brand_ids),
            "OrderBy": "dist",
        })
        body = await self._get(url)
        return self._parse_gas_items(body, uat_id)

    @staticmethod
    def _parse_gas_items(body: bytes, uat_id: str) -> list[FuelPriceItem]:
        try:
            root = ET.fromstring(body)
        except ET.ParseError as err:
            raise FuelPricesApiError(f"Invalid XML: {err}") from err

        items: list[FuelPriceItem] = []
        for prod in root.iter(f"{{{XMLNS}}}GasProduct"):
            try:
                catprod = prod.find("d:Catprod", NS)
                network = prod.find("d:Network", NS)
                price_el = prod.find("d:Price", NS)
                if catprod is None or network is None or price_el is None:
                    continue
                if not (price_el.text and price_el.text.strip()):
                    continue

                catprod_id = _text(catprod, "d:Id")
                brand_id = _text(network, "d:Id")
                if not catprod_id or not brand_id:
                    continue

                items.append(FuelPriceItem(
                    uat_id=uat_id,
                    station_id=_text(prod, "d:Stationid") or "unknown",
                    brand_id=brand_id,
                    brand_name=_text(network, "d:Name") or brand_id,
                    catprod_id=catprod_id,
                    catprod_name=_text(catprod, "d:Name") or "",
                    product_name=_text(prod, "d:Name") or "",
                    price=float(price_el.text),
                    distance_km=_safe_float(_text(prod, "d:Distance")),
                ))
            except (ValueError, AttributeError) as err:
                _LOGGER.debug("Skipping malformed GasProduct: %s", err)
        return items

    # -----------------------------------------------------------------
    # Catalog (cities + brands)
    # -----------------------------------------------------------------
    async def fetch_uat_list(self) -> list[dict[str, str]]:
        """Return the default list of UATs (top ~20 cities)."""
        body = await self._get(URL(URL_UAT_LIST))
        try:
            root = ET.fromstring(body)
        except ET.ParseError as err:
            raise FuelPricesApiError(f"Invalid UAT XML: {err}") from err

        out: list[dict[str, str]] = []
        for uat in root.iter(f"{{{XMLNS}}}UAT"):
            uat_id = _text(uat, "d:Id")
            uat_name = _text(uat, "d:Name")
            if uat_id and uat_name:
                out.append({"id": uat_id, "name": uat_name})
        return out

    async def fetch_brands(self) -> list[dict[str, str]]:
        """Return the canonical brand list."""
        body = await self._get(URL(URL_GAS_NETWORKS))
        try:
            root = ET.fromstring(body)
        except ET.ParseError as err:
            raise FuelPricesApiError(f"Invalid brand XML: {err}") from err

        out: list[dict[str, str]] = []
        for net in root.iter(f"{{{XMLNS}}}GasNetwork"):
            brand_id = _text(net, "d:Id")
            if brand_id:
                out.append({
                    "id": brand_id,
                    "name": _text(net, "d:Name") or brand_id,
                })
        return out

    # -----------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------
    async def _get(self, url: URL) -> bytes:
        try:
            async with self._session.get(
                str(url),
                headers=self._headers,
                timeout=self._timeout,
            ) as resp:
                resp.raise_for_status()
                return await resp.read()
        except aiohttp.ClientError as err:
            raise FuelPricesApiError(f"HTTP failure: {err}") from err


def _text(elem: ET.Element, path: str) -> str | None:
    found = elem.find(path, NS)
    return found.text if found is not None else None


def _safe_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
