# Fuel Prices Romania — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/mocanu-alexandru/ha-fuel-prices-ro/actions/workflows/validate.yml/badge.svg)](https://github.com/mocanu-alexandru/ha-fuel-prices-ro/actions/workflows/validate.yml)

Pulls daily fuel prices for Romanian gas stations (per city + per brand) from the
official source — Consiliul Concurenței's `monitorulpreturilor.info` — and exposes
them as Home Assistant sensors with native long-term statistics support.

## Features

- **Per-city, per-brand, per-fuel sensors** — track exactly the combinations you care about
- **All major Romanian brands**: OMV, Petrom, Rompetrol, MOL, Lukoil, Socar, Gazprom
- **5 fuel categories**: Benzină standard / premium, Motorină standard / premium, GPL
- **Long-term statistics** out of the box (`state_class: measurement`) — perfect for `apexcharts-card`
- **Polite polling** — one config-flow-driven entry per city, ~5 API calls every 6 hours
- **All-stations data** in entity attributes — see every station's price, not just the cheapest
- **Romanian + English UI** translations included

## Installation

### Via HACS (recommended)

1. In HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add `https://github.com/mocanu-alexandru/ha-fuel-prices-ro` as type **Integration**
3. Install **Fuel Prices Romania**
4. Restart Home Assistant
5. **Settings → Devices & Services → Add Integration → Fuel Prices Romania**

### Manual

Copy `custom_components/fuel_prices_ro/` into your Home Assistant
`config/custom_components/` directory and restart.

## Configuration

Two-step UI wizard:

1. **Pick a city** — dropdown populated live from the API (~20 major UATs;
   falls back to a bundled list if the API is unreachable)
2. **Pick brands + fuels + interval** — multi-select, with all brands and
   fuels selected by default; refresh interval defaults to 6h

You can add **multiple cities** (one config entry each) and tweak selections
later via **Configure** on the integration card.

## Sensor naming

For an entry on Iași with OMV + Petrom and Benzină standard + Motorină
standard, the integration creates four entities:

| Entity ID                                          | Native value | Attributes |
|----------------------------------------------------|-------------:|------------|
| `sensor.fuel_prices_iași_omv_benzina_standard`     | `8.99 RON/L` | `min_station_id`, `min_product_name`, `stations_count`, `all_stations[]`, … |
| `sensor.fuel_prices_iași_omv_motorina_standard`    | `9.45 RON/L` | (same) |
| `sensor.fuel_prices_iași_petrom_benzina_standard`  | `8.97 RON/L` | (same) |
| `sensor.fuel_prices_iași_petrom_motorina_standard` | `9.43 RON/L` | (same) |

The state shows the **minimum price** across all stations of that brand in
that city. Full per-station prices are available in `all_stations`.

## Dashboard example (apexcharts-card)

```yaml
type: custom:apexcharts-card
header:
  title: Fuel prices — Iași
  show: true
graph_span: 30d
span:
  end: day
yaxis:
  - min: 4
    max: 12
    decimals: 2
    apex_config:
      title:
        text: RON/L
series:
  - entity: sensor.fuel_prices_iași_omv_benzina_standard
    name: OMV Benzină
    stroke_width: 2
    type: line
  - entity: sensor.fuel_prices_iași_petrom_benzina_standard
    name: Petrom Benzină
    stroke_width: 2
    type: line
  - entity: sensor.fuel_prices_iași_omv_motorina_standard
    name: OMV Motorină
    stroke_width: 2
    type: line
    color: "#e76f51"
  - entity: sensor.fuel_prices_iași_petrom_motorina_standard
    name: Petrom Motorină
    stroke_width: 2
    type: line
    color: "#f4a261"
```

## How it works

The integration calls the (undocumented but stable) WCF/REST endpoint:

```
GET https://monitorulpreturilor.info/pmonsvc/Gas/GetGasItemsByUat
    ?UatId={uat_id}
    &CSVGasCatalogProductIds={fuel_id}
    &CSVGasNetworkIDS={brand_a},{brand_b},…
    &OrderBy=dist
```

Returns XML with one `<GasProduct>` per (station × brand × fuel variant). The
coordinator runs **one call per fuel category** (the API rejects CSV in
`CSVGasCatalogProductIds`), aggregates by `(brand, fuel)` and exposes the
minimum + station list as a single sensor.

City list comes from `GET /pmonsvc/Gas/GetUatByName` (no params returns the top
~20 UATs). Brand catalog from `GET /pmonsvc/Gas/GetGasNetworks`.

### Fallback source (since v0.1.3)

If the primary Consiliul Concurenței source fails for a fuel category, the
coordinator falls back **per-fuel** to [peco-online.ro](https://www.peco-online.ro)
— an independent aggregator with its own crawl — by POSTing its public search
form and parsing the returned station list. This keeps real, current prices
flowing during a sustained primary-source outage (like the multi-week TLS-chain
break in mid-2026) instead of letting sensors go `unavailable`.

The `source` attribute on each sensor shows where the live value came from
(`primary` = Council, `fallback` = peco-online.ro). The fallback covers only the
bundled default cities + the 7 known brands, has no public API (so it scrapes
and is best-effort), and may report a slightly different set of stations than
the primary source.

## Limits & disclaimers

- The pmonsvc API is **not officially documented**. The integration is built
  off reverse-engineering of the public website's traffic. It has been stable
  since 2019 but could change without notice.
- Only the ~20 default UATs returned by `GetUatByName` are available out of
  the box. Smaller towns are not exposed. (PR welcome to add a manual UAT-ID
  entry mode.)
- Prices reflect what gas station chains report to Consiliul Concurenței —
  there can be lag of a day or two vs. the actual pump.
- Data: © Consiliul Concurenței. This integration only redistributes
  publicly available figures; **respect their terms of use**.
- **Upstream TLS chain workaround (since v0.1.2):** `monitorulpreturilor.info`
  currently serves an incomplete certificate chain (the issuing Sectigo R36
  intermediate is missing), which makes Python/aiohttp reject the connection
  with `unable to get local issuer certificate`. Web browsers hide this by
  fetching the missing intermediate via AIA; Python does not. The integration
  ships the missing intermediate (`sectigo_r36_intermediate.pem`) and completes
  the chain itself — certificate verification stays **fully enabled**. This is
  a server-side misconfiguration on the upstream host; the workaround becomes
  harmless once they fix it.

## License

MIT — see [`LICENSE`](LICENSE).

## Acknowledgements

- Built for the Romanian Home Assistant community 🇷🇴
- Data source: [monitorulpreturilor.info](https://monitorulpreturilor.info/Home/Gas)
- Inspired by similar fuel-price integrations in IT, FR, ES, BE, NL, UK, AU
# ha-fuel-prices-ro
