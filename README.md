# Open GHG Emission Factor Register

An open, citation-first catalogue of **28,881 real greenhouse-gas emission factors** from **8 datasets covering ~200 countries**, extracted programmatically from official sources, for corporate carbon accounting under the GHG Protocol — filed by scope, GHG Protocol category, country/region, year, and publishing organization, with spend-based and physical (weight/activity) methods labelled separately. Countries are shown by full name throughout the site (a `data/country-names.json` lookup backs the ISO codes stored in each record).

## What's loaded right now

| Source | Countries | Records | Coverage |
|---|---|---:|---|
| UK DESNZ/Defra — GHG Conversion Factors 2025 | United Kingdom | 6,973 | Fuels, refrigerants, vehicles, electricity, heat & steam, well-to-tank, water, waste, materials, business travel, hotels, homeworking |
| US EPA — GHG Emission Factors Hub (Jan 2025) | United States | 1,029 | Stationary & mobile combustion, purchased electricity, steam/heat, transport & distribution, waste, business travel/commuting |
| US EPA — eGRID2023 (rev2) | United States | 7,632 | Electricity GHG rates at subregion, state, NERC region, balancing-authority, and national level |
| NZ Ministry for the Environment — Measuring Emissions 2026 | New Zealand | 3,252 | Fuel, refrigerants, agriculture/forestry, purchased electricity/heat/steam, travel, freight, materials & waste, water, working-from-home |
| India CEA — CO2 Baseline Database v21.0 | India | 958 | National grid headline factors (weighted average, OM/BM/CM) plus ~950 individual thermal generating units' specific CO2 rate |
| Canada ECCC — Federal GHG Offset System factors | Canada | 558 | Natural gas (CO2/CH4/N2O) by province, NGL & refined petroleum products, provincial electricity intensity, biogas N2O, enteric fermentation & manure management Tier-2 factors |
| Eurostat/EEA — GHG intensity by NACE sector | 27 EU countries + Norway, Iceland, Switzerland, Serbia, Turkey | 8,079 | Spend-based GHG intensity (gCO2e/EUR of output or value-added) across 79 economic sectors, 2023–2024 — the register's first real spend-based dataset |
| Ember — Yearly Electricity Data | ~200 countries incl. China, Germany, France, Denmark | 400 | Scope 2 location-based national grid electricity CO2e intensity (gCO2e/kWh), 2023–2024 |
| **Total** | **~200 countries** | **28,881** | |

Every one of these values was read by a Python parser (`etl/`) directly out of the publisher's own spreadsheet, API, or published HTML table — never typed by hand. The Canada and Eurostat parsers in particular pull from a live government page and a REST API rather than a downloadable file, since neither publisher offers one; Ember is the one non-government source here — it's an independent energy think tank that compiles the closest thing to a single-source international electricity grid factor for countries (like China) whose own environment ministry doesn't publish an English-language equivalent to Defra or EPA's tables. `data/sources.json` also lists agencies known but not yet integrated (IPCC EFDB, ADEME, Australia DCCEEW — unreachable from this build environment, Japan, Brazil, China's own MEE grid factors, …) with `"populated": false`, plus a separate list of **paid/commercial providers** (IEA, ecoinvent, Climatiq, Sphera, S&P Global Trucost, Carbon Minds) for factors outside what free government data covers — also shown on the site itself, in the "Need a factor that isn't here?" section.

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
