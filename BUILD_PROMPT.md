# Build prompt — Open GHG Emission Factor Register

Copy everything below the line into Claude (or any capable model) to generate / extend the project.

---

You are building **an open-source, static, GitHub-hostable web application that catalogues greenhouse-gas (GHG) emission factors** so that companies can use it for corporate carbon accounting under the GHG Protocol.

## 1. Scope of the dataset

Every record in the register is **one emission factor**. It must carry all of the following fields:

| Field | Type | Notes |
|---|---|---|
| `id` | string | stable slug, e.g. `uk-desnz-2024-natural-gas-kwh` |
| `activity` | string | plain-language name of what is being measured |
| `scope` | `1` \| `2` \| `3` | GHG Protocol scope |
| `category` | `3.1`–`3.15`, or `1`, `2` | Scope 3 category number |
| `category_name` | string | e.g. "Purchased goods and services" |
| `method` | `spend-based` \| `weight-based` \| `activity-based` \| `average-data` \| `supplier-specific` \| `hybrid` | |
| `value` | number \| null | the factor itself |
| `unit_numerator` | string | `kgCO2e`, `tCO2e`, `gCO2e` |
| `unit_denominator` | string | `USD`, `EUR`, `INR`, `kg`, `tonne`, `kWh`, `litre`, `tonne-km`, `passenger-km`, `night`, `m3` |
| `gases` | array | e.g. `["CO2","CH4","N2O"]` — state whether the factor is CO2e or a single gas |
| `gwp_basis` | string | e.g. `IPCC AR6 GWP100`, `IPCC AR5 GWP100` |
| `country` | ISO 3166-1 alpha-2, or `GLOBAL` / region code | |
| `year` | integer | **reference year of the underlying data**, not the publication year |
| `publication_year` | integer | |
| `organization` | string | the publishing body (see source registry below) |
| `dataset` | string | the specific dataset/table name |
| `source_url` | URL | direct link to the page or file it was taken from |
| `source_page_or_table` | string | sheet name, table number, row label — so anyone can re-verify |
| `licence` | string | e.g. `OGL v3`, `Public domain (US Gov)`, `CC-BY-4.0`, `Proprietary — licence required` |
| `price_year` | integer \| null | **required for every spend-based factor** — the currency base year |
| `currency_deflator_note` | string \| null | how to inflate/deflate to the user's reporting year |
| `boundary` | string | e.g. `cradle-to-gate`, `well-to-tank`, `tank-to-wheel`, `WTT+TTW` |
| `value_status` | `verified` \| `unverified` \| `placeholder` | never publish a number as verified unless a human checked it against `source_url` |
| `notes` | string | caveats, exclusions, known double-counting risks |

**Hard rule: never invent a numeric factor.** If the number has not been read off the cited source, `value` must be `null` and `value_status` must be `placeholder`. A missing number with a good citation is useful; a fabricated number is a reporting liability for the company using it.

## 2. Source registry (organizations to cover)

Build a separate `sources.json` describing each publisher: name, country/region, coverage, update cadence, licence, whether free, and homepage.

Cover at minimum:

- **UK DESNZ / DEFRA** — GHG Conversion Factors for Company Reporting (annual, Open Government Licence)
- **US EPA** — GHG Emission Factors Hub (annual)
- **US EPA** — Supply Chain GHG Emission Factors (USEEIO), spend-based by NAICS, kgCO2e/USD
- **US EPA** — eGRID, grid electricity by subregion
- **IPCC** — Emission Factor Database (EFDB) and 2006 Guidelines + 2019 Refinement
- **IEA** — Emissions Factors (electricity by country, licensed)
- **ADEME** — Base Empreinte (France)
- **EXIOBASE / GLORIA / Eora** — multi-region input-output, spend-based, many countries
- **ecoinvent** — process LCA (licensed)
- **Environment and Climate Change Canada** — National Inventory Report
- **Australia** — National Greenhouse Accounts Factors (DCCEEW)
- **India** — CEA CO2 Baseline Database (grid), BEE
- **Japan** — MOE/METI emission factor lists
- **China** — MEE grid emission factors
- **EU** — EEA, EU ETS benchmarks, PEF datasets
- **Brazil** — MCTI grid factors
- **GHG Protocol / GLEC Framework** — freight and logistics
- **Aggregators** — Climatiq, Carbon Minds, Sphera, Ecoinvent-derived commercial APIs (mark licence clearly)

## 3. Scope 3 taxonomy (drive the whole UI off this)

3.1 Purchased goods and services · 3.2 Capital goods · 3.3 Fuel- and energy-related activities · 3.4 Upstream transportation and distribution · 3.5 Waste generated in operations · 3.6 Business travel · 3.7 Employee commuting · 3.8 Upstream leased assets · 3.9 Downstream transportation and distribution · 3.10 Processing of sold products · 3.11 Use of sold products · 3.12 End-of-life treatment of sold products · 3.13 Downstream leased assets · 3.14 Franchises · 3.15 Investments

## 4. Application requirements

- **Static only.** No backend, no build step required. Must run from `file://` and from GitHub Pages. Data lives in `/data/*.json`; the page fetches it, with an inline fallback so it also works when opened directly.
- **Filters:** category 3.1–3.15 (plus scope 1 and 2), country, year, organization, method (spend vs weight/activity), free-text search.
- **Sort** by year, country, organization, value.
- **Every row must show its source and link.** A row without a citation must not render.
- **Detail view** per factor: full metadata, the exact worked formula, and a copy-to-clipboard citation string.
- **Calculator:** user enters an activity amount (spend or mass or kWh) → returns kgCO2e, showing the arithmetic. For spend-based factors, require the user to state their spend year and warn if it differs from `price_year`.
- **Export:** CSV and JSON download of the current filtered view.
- **Contribution flow:** a documented JSON schema, a `CONTRIBUTING.md`, and a GitHub Actions workflow that validates every PR against the schema (required fields present, `source_url` reachable, no `verified` row with a null value).
- Accessible: keyboard navigable, visible focus, respects `prefers-reduced-motion`, works on mobile.

## 5. Methodology page (write this as real content, not filler)

Explain, with worked examples:
- **Spend-based**: `emissions = spend × EEIO factor`, when to use it (early-stage screening, long-tail suppliers), why it is weak (price ≠ physical impact, inflation sensitivity, sector averaging), and how to deflate spend to the factor's price year.
- **Weight/average-data**: `emissions = mass × factor`, better for commodities.
- **Supplier-specific**: highest quality, replaces the above.
- **Data quality hierarchy** and how to record it.
- **Double-counting** risks between 3.1 and 3.3/3.4.
- **Market-based vs location-based** scope 2.
- A blunt disclaimer: this register is a research aid, not assurance-ready data; users must verify against the primary source before reporting.

## 6. Repository deliverables

`index.html`, `data/factors.json`, `data/sources.json`, `data/schema.json`, `README.md`, `CONTRIBUTING.md`, `LICENSE` (CC-BY-4.0 for the compilation; per-record licences respected and stated), `.github/workflows/validate.yml`.

## 7. Design direction

Treat it as a scientific register, not a SaaS landing page. Data-dense, monospaced numerics, restrained palette, one memorable structural device. Avoid the generic cream/serif/terracotta look. Type must make numbers legible and comparable.
