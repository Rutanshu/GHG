"""
Parse the New Zealand Ministry for the Environment 'Measuring Emissions'
Emission Factors Flat File (long format) into normalized emission-factor
records.

Source: https://environment.govt.nz/publications/measuring-emissions-guide-2025/
File used: emission_factors_2026_v2_long.csv (official machine-readable export)
"""
import csv
import json
import re
import os

SRC_PATH = "raw/nz-mfe-2026-long.csv"
OUT_PATH = "out/nz-mfe-2026.json"

SOURCE_URL = "https://measuringemissionsguide.environment.govt.nz/"
ORG = "New Zealand Ministry for the Environment (MfE)"
DATASET = "Measuring Emissions: A Guide for Organisations — Emission Factors 2026 (v2)"
LICENCE = "Crown copyright — reuse permitted with attribution (CC BY 4.0 NZ Government)"
YEAR = 2026

# Page (top grouping) -> (scope, GHG Protocol category code, category name)
PAGE_MAP = {
    "Fuel": (1, "1", "Scope 1 direct"),
    "Refrigerant and Other Gases": (1, "1", "Scope 1 direct"),
    "Agriculture, forestry and other land uses": (1, "1", "Scope 1 direct"),
    "Purchased Electricity, Heat, and Steam": (2, "2", "Scope 2 purchased energy"),
    "Travel": (3, "3.6", "Business travel"),
    "Freight Transport": (3, "3.4", "Upstream transportation and distribution"),
    "Indirect Business Related": (3, "3.7", "Employee commuting"),
}
# Materials and Waste / Water Supply and Wastewater are split by Section below.

GAS_CODE_MAP = {
    "GHG_CO2_KGCO2_e": ["CO2"],
    "GHG_CH4_KGCO2_e": ["CH4"],
    "GHG_N2O_KGCO2_e": ["N2O"],
    "GHG_BCO2_KGCO2_e": ["CO2-biogenic"],
    "GHG_TOTAL_KGCO2_e": ["CO2", "CH4", "N2O"],
}


def slugify(uuid, ghg):
    return "nz-mfe-2026-" + re.sub(r"[^a-z0-9]+", "-", (uuid + "-" + ghg).lower()).strip("-")


def category_for(page, section):
    if page in PAGE_MAP:
        return PAGE_MAP[page]
    if page == "Materials and Waste":
        return (3, "3.5", "Waste generated in operations")
    if page == "Water Supply and Wastewater":
        if "Wastewater" in section:
            return (3, "3.5", "Waste generated in operations")
        return (3, "3.1", "Purchased goods and services")
    return (3, "3", "Scope 3 (unclassified)")


def boundary_for(page, section):
    if page == "Purchased Electricity, Heat, and Steam":
        return "generation (location-based grid average)"
    if page in ("Travel", "Freight Transport"):
        return "distance-based (tank-to-wheel)"
    if page == "Materials and Waste":
        return "disposal / end-of-life treatment"
    if page == "Water Supply and Wastewater":
        return "supply / treatment"
    return "combustion / direct activity"


def main():
    records = []
    skipped_blank = 0
    seen_ids = set()

    with open(SRC_PATH, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            val = row["EmissionFactor"].strip()
            if val == "":
                skipped_blank += 1
                continue
            gas_key = row["GHG"].strip()
            gases = GAS_CODE_MAP.get(gas_key, [gas_key])
            page, section = row["Page"], row["Section"]
            scope, cat, cat_name = category_for(page, section)

            breadcrumb = " > ".join(p for p in (page, section, row["SubSection"], row["EmissionsFactorLabel"]) if p)
            activity = f"{page} — {row['EmissionsFactorLabel']}" + (f" ({section})" if section and section != page else "")

            base_id = slugify(row["UUID"], gas_key)
            rid, n = base_id, 2
            while rid in seen_ids:
                rid = f"{base_id}-{n}"
                n += 1
            seen_ids.add(rid)

            rec = {
                "id": rid,
                "activity": activity,
                "scope": scope,
                "category": cat,
                "category_name": cat_name,
                "method": "activity-based",
                "value": round(float(val), 6),
                "unit_numerator": "kgCO2e",
                "unit_denominator": row["Unit"],
                "gases": gases,
                "gwp_basis": "IPCC AR5 GWP100",
                "country": "NZ",
                "region": None,
                "year": YEAR,
                "publication_year": YEAR,
                "organization": ORG,
                "dataset": DATASET,
                "source_url": SOURCE_URL,
                "source_page_or_table": f"Emission Factors Flat File — {breadcrumb} [{gas_key}] — UUID {row['UUID']}",
                "licence": LICENCE,
                "price_year": None,
                "currency_deflator_note": None,
                "boundary": boundary_for(page, section),
                "value_status": "verified",
                "notes": (f"Uncertainty: {row['Uncertainties']}." if row["Uncertainties"] else None),
            }
            records.append(rec)

    print(f"NZ MfE: {len(records)} records, {skipped_blank} skipped (blank value)")
    ids = [r["id"] for r in records]
    assert len(ids) == len(set(ids)), "duplicate ids in NZ output!"

    os.makedirs("out", exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(records, f, ensure_ascii=False)
    print("wrote", OUT_PATH)


if __name__ == "__main__":
    main()
