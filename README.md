# Open GHG Emission Factor Register

An open, citation-first catalogue of **20,371 real greenhouse-gas emission factors** from **6 government datasets across 5 countries**, extracted programmatically from official sources, for corporate carbon accounting under the GHG Protocol — filed by scope, GHG Protocol category, country/region, year, and publishing organization, with spend-based and physical (weight/activity) methods labelled separately.

## What's loaded right now

| Source | Country | Records | Coverage |
|---|---|---:|---|
| UK DESNZ/Defra — GHG Conversion Factors 2025 | GB | 6,973 | Fuels, refrigerants, vehicles, electricity, heat & steam, well-to-tank, water, waste, materials, business travel, hotels, homeworking |
| US EPA — GHG Emission Factors Hub (Jan 2025) | US | 1,029 | Stationary & mobile combustion, purchased electricity, steam/heat, transport & distribution, waste, business travel/commuting |
| US EPA — eGRID2023 (rev2) | US | 7,632 | Electricity GHG rates at subregion, state, NERC region, balancing-authority, and national level |
| NZ Ministry for the Environment — Measuring Emissions 2026 | NZ | 3,252 | Fuel, refrigerants, agriculture/forestry, purchased electricity/heat/steam, travel, freight, materials & waste, water, working-from-home |
| India CEA — CO2 Baseline Database v21.0 | IN | 958 | National grid headline factors (weighted average, OM/BM/CM) plus ~950 individual thermal generating units' specific CO2 rate |
| Canada ECCC — Federal GHG Offset System factors | CA | 527 | Natural gas (CO2/CH4/N2O) by province, NGL & refined petroleum products, provincial electricity intensity, biogas N2O |
| **Total** | **5 countries** | **20,371** | |

Every one of these values was read by a Python parser (`etl/`) directly out of the publisher's own spreadsheet or published HTML table — never typed by hand. `data/sources.json` also lists agencies known but not yet integrated (IPCC EFDB, IEA, ADEME, Australia DCCEEW — unreachable from this build environment, EU, Japan, …) with `"populated": false`, as the map for extending this further.

## Why it exists

Emission factors are scattered across dozens of government and research publishers, in spreadsheets with inconsistent units, boundaries, and price years. Companies end up copying numbers with no record of where they came from. This register stores the **provenance first**: organization, dataset, direct URL, sheet or table, licence, boundary, GWP basis, and — for spend-based factors — the currency price year.

## The honesty rule

`value_status: "verified"` means the value was extracted mechanically from the cited primary-source file — not invented, not hand-typed. Every record's `source_page_or_table` names the exact sheet/table/unit it came from so you can re-open `source_url` and check it. Single-gas rows keep their native unit (e.g. `kgCH4`, `gN2O`) rather than being silently force-converted to CO2e.

Records from licensed datasets (ecoinvent, IEA) keep the citation and units but must not carry redistributed values.

## Run it

```bash
git clone <your-repo>
cd <your-repo>
python3 -m http.server 8000
# open http://localhost:8000
```

Opening `index.html` straight from disk will not work — browsers block `fetch` on `file://`. Use the local server, or publish.

## Publish on GitHub Pages

1. Push to a public repo.
2. **Settings → Pages → Source: Deploy from a branch → `main` / root.**
3. It goes live at `https://<user>.github.io/<repo>/`.

No build step, no dependencies, no backend.

## Files

| Path | Purpose |
|---|---|
| `index.html` | The whole application |
| `data/index.json` | Manifest — lists each dataset file, its record count and label; the page fetches all of them in parallel |
| `data/factors/*.json` | The register, one file per source dataset |
| `data/sources.json` | Publisher registry — coverage, cadence, licence, whether currently populated |
| `data/schema.json` | JSON Schema every record must satisfy |
| `etl/` | Python parsers that turned each publisher's raw spreadsheet into `data/factors/*.json` (`parse_defra.py`, `parse_epa_hub.py`, `parse_egrid.py`, `combine.py`) |
| `etl/raw/` | The unmodified source spreadsheets, kept for provenance |
| `BUILD_PROMPT.md` | The prompt used to generate and extend this project |

## Contributing

To add a new agency: write a parser in `etl/` that reads the publisher's own file (spreadsheet, CSV, API) and emits records in the schema shape, run it into `data/factors/<slug>.json`, then run `python3 etl/combine.py` to validate everything and regenerate `data/index.json`. To add one-off records by hand, add them to the relevant `data/factors/*.json` file directly. Required in every record: a working `source_url`, a `source_page_or_table` precise enough for a stranger to re-verify, and a `price_year` on anything spend-based. A `verified` record must carry a real, source-derived number — never a guess.

## Licence

Compilation: CC BY 4.0. Each record remains under its publisher's own licence, stated in the row. This is a research aid, not assurance-ready data. The reporting entity is responsible for verification.
