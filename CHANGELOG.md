# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
