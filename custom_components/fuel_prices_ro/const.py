"""Constants for the Romanian Fuel Prices integration."""
from __future__ import annotations

import json
from pathlib import Path

DOMAIN = "fuel_prices_ro"

_manifest = json.loads((Path(__file__).parent / "manifest.json").read_text())
_VERSION = _manifest["version"]
ATTRIBUTION = "Data: Consiliul Concurenței (monitorulpreturilor.info)"

# ---------------------------------------------------------------------------
# API endpoints (discovered via discovery script — see README)
# ---------------------------------------------------------------------------
PMONSVC_BASE = "https://monitorulpreturilor.info/pmonsvc/Gas"
URL_GAS_ITEMS = f"{PMONSVC_BASE}/GetGasItemsByUat"
URL_GAS_NETWORKS = f"{PMONSVC_BASE}/GetGasNetworks"
URL_UAT_LIST = f"{PMONSVC_BASE}/GetUatByName"

# ---------------------------------------------------------------------------
# Fallback source: peco-online.ro (independent crawl, used only if the primary
# Council source fails). No public API — we POST the same form its website uses
# and parse the server-rendered `rezultate` JSON. See peco_api.py.
# ---------------------------------------------------------------------------
URL_PECO_FALLBACK = "https://www.peco-online.ro/index_en.php"

# Our fuel-category id -> peco `carburant` value (verified 1:1).
PECO_FUEL_MAP: dict[str, str] = {
    "11": "Benzina_Regular",
    "12": "Benzina_Premium",
    "21": "Motorina_Regular",
    "22": "Motorina_Premium",
    "31": "GPL",
}

# Our brand id -> peco `retea` value. peco returns the same names title-cased,
# so the reverse map is simply `.upper()` (validated against BRANDS on parse).
PECO_BRAND_MAP: dict[str, str] = {
    "GAZPROM": "Gazprom",
    "LUKOIL": "Lukoil",
    "MOL": "Mol",
    "OMV": "OMV",
    "PETROM": "Petrom",
    "ROMPETROL": "Rompetrol",
    "SOCAR": "Socar",
}

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_SCAN_INTERVAL_HOURS = 6
HTTP_TIMEOUT_SECONDS = 15
USER_AGENT = f"ha-fuel-prices-ro/{_VERSION} (Home Assistant)"

# ---------------------------------------------------------------------------
# Configuration keys
# ---------------------------------------------------------------------------
CONF_UAT_ID = "uat_id"
CONF_UAT_NAME = "uat_name"
CONF_BRANDS = "brands"
CONF_FUELS = "fuels"
CONF_SCAN_INTERVAL = "scan_interval_hours"

# ---------------------------------------------------------------------------
# Static catalog (discovered & locked — these IDs are stable)
# ---------------------------------------------------------------------------

# Catprod (fuel category) IDs from Consiliul Concurenței
FUEL_CATEGORIES: dict[str, str] = {
    "11": "Benzină standard",
    "12": "Benzină premium",
    "21": "Motorină standard",
    "22": "Motorină premium",
    "31": "GPL",
}

# MDI icons per fuel category
FUEL_ICONS: dict[str, str] = {
    "11": "mdi:gas-station",
    "12": "mdi:gas-station-outline",
    "21": "mdi:truck-fast",
    "22": "mdi:truck-fast-outline",
    "31": "mdi:gas-cylinder",
}

# Slug used in entity_ids — diacritics stripped, snake_case
FUEL_SLUGS: dict[str, str] = {
    "11": "benzina_standard",
    "12": "benzina_premium",
    "21": "motorina_standard",
    "22": "motorina_premium",
    "31": "gpl",
}

# Gas station brands
BRANDS: dict[str, str] = {
    "GAZPROM": "Gazprom",
    "LUKOIL": "Lukoil",
    "MOL": "MOL",
    "OMV": "OMV",
    "PETROM": "Petrom",
    "ROMPETROL": "Rompetrol",
    "SOCAR": "Socar",
}

# Default UAT (city) list discovered via GetUatByName(no params).
# The integration also tries to fetch this live from the API at first setup
# and falls back to this hardcoded list if the call fails.
DEFAULT_UATS: dict[str, str] = {
    "20297":  "Bacău",
    "26564":  "Oradea",
    "40198":  "Brașov",
    "42682":  "Brăila",
    "44818":  "Buzău",
    "54975":  "Cluj-Napoca",
    "60419":  "Constanța",
    "69900":  "Craiova",
    "75098":  "Galați",
    "92701":  "Fetești",
    "95060":  "Iași",
    "130534": "Ploiești",
    "131256": "Câmpina",
    "155243": "Timișoara",
    "179132": "București",
}
