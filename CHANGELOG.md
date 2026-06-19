# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.2] - 2026-06-19

### Fixed
- Sensors no longer go `unavailable` due to TLS verification failures
  (`unable to get local issuer certificate` / `CERTIFICATE_VERIFY_FAILED`).
  The upstream host `monitorulpreturilor.info` renewed its certificate but
  now serves an incomplete chain — the issuing Sectigo "R36" intermediate is
  missing. Browsers recover via AIA fetching, but Python/aiohttp do not. The
  integration now bundles the missing intermediate (and its R46 root) and
  completes the chain itself, **without disabling certificate verification**.
  Becomes harmless once the upstream operator fixes their server config.

## [0.1.0] - 2026-05-06

### Added
- Initial release.
- Per-city, per-brand, per-fuel sensors for Romanian gas stations.
- Two-step config flow (city → brands + fuels + interval).
- Options flow for editing brands, fuels, and refresh interval.
- Live UAT list fetched from `GetUatByName`, with bundled fallback for
  the top 15 Romanian cities.
- 5 fuel categories: Benzină standard / premium, Motorină standard / premium, GPL.
- 7 brands: OMV, Petrom, Rompetrol, MOL, Lukoil, Socar, Gazprom.
- Romanian + English translations.
- HACS-compatible repository structure with hassfest + HACS Action CI.
