"""
Parse the UK DESNZ/Defra 'GHG Conversion Factors 2025' flat file
(sheet 'Factors by Category') into normalized emission-factor records.

Source: https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025
File used: ghg-conversion-factors-2025-flat-format.xlsx (official "for automatic processing" export)
"""
import json
import re
import openpyxl

SRC_PATH = "raw/defra-2025-flat.xlsx"
OUT_PATH = "out/defra-2025.json"

SOURCE_URL = "https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2025"
ORG = "UK Department for Energy Security & Net Zero (DESNZ) / Defra"
DATASET = "UK Government GHG Conversion Factors for Company Reporting 2025"
LICENCE = "Open Government Licence v3.0"
YEAR = 2025

# Level 1 (top sheet grouping) -> best-effort GHG Protocol Scope 3 category.
# This is organisational metadata only (industry-standard, well-documented
# correspondences) — it never touches the numeric value, which is read
# verbatim from the source cell.
L1_TO_CAT3 = {
    "Freighting goods": ("3.4", "Upstream transportation and distribution"),
    "WTT- delivery vehs & freight": ("3.3", "Fuel- and energy-related activities"),
    "WTT- fuels": ("3.3", "Fuel- and energy-related activities"),
    "WTT- bioenergy": ("3.3", "Fuel- and energy-related activities"),
    "WTT- pass vehs & travel- land": ("3.3", "Fuel- and energy-related activities"),
    "WTT- business travel- air": ("3.3", "Fuel- and energy-related activities"),
    "WTT- business travel- sea": ("3.3", "Fuel- and energy-related activities"),
    "WTT- heat and steam": ("3.3", "Fuel- and energy-related activities"),
    "WTT- UK electricity": ("3.3", "Fuel- and energy-related activities"),
    "Business travel- land": ("3.6", "Business travel"),
    "Business travel- air": ("3.6", "Business travel"),
    "Business travel- sea": ("3.6", "Business travel"),
    "Hotel stay": ("3.6", "Business travel"),
    "Homeworking": ("3.7", "Employee commuting"),
    "Waste disposal": ("3.5", "Waste generated in operations"),
    "Water treatment": ("3.5", "Waste generated in operations"),
    "Water supply": ("3.1", "Purchased goods and services"),
    "Material use": ("3.1", "Purchased goods and services"),
    "Passenger vehicles": ("3.6", "Business travel"),
    "Delivery vehicles": ("3.9", "Downstream transportation and distribution"),
    "SECR kWh pass & delivery vehs": ("3.6", "Business travel"),
    "SECR kWh UK electricity for EVs": ("3.3", "Fuel- and energy-related activities"),
    "UK electricity for EVs": ("3.3", "Fuel- and energy-related activities"),
    "UK electricity T&D for EVs": ("3.3", "Fuel- and energy-related activities"),
}
# Level1 groups that represent an organisation's own assets -> Scope 1 territory
# (still labelled per the row's own Scope column; this dict is unused for those).

GAS_RE = re.compile(r"of (CO2|CH4|N2O) per unit", re.I)


def slugify(row_id: str) -> str:
    return "defra-2025-" + re.sub(r"[^a-z0-9]+", "-", row_id.lower()).strip("-")


def gases_for(ghg_unit: str):
    if ghg_unit.strip().lower() == "kg co2e":
        return ["CO2", "CH4", "N2O"]
    m = GAS_RE.search(ghg_unit)
    return [m.group(1).upper()] if m else ["CO2e"]


def category_for(scope_label: str, level1: str):
    if scope_label == "Scope 1":
        return "1", "Scope 1 direct", 1
    if scope_label == "Scope 2":
        return "2", "Scope 2 purchased energy", 2
    if scope_label == "Scope 3":
        cat, name = L1_TO_CAT3.get(level1, (None, None))
        if cat:
            return cat, name, 3
        return "3", "Scope 3 (unclassified sub-category)", 3
    return None, None, None


def boundary_for(level1: str) -> str:
    if level1.startswith("WTT-") or level1.startswith("WTT "):
        return "well-to-tank (upstream fuel/energy supply chain)"
    if level1 in ("UK electricity", "Overseas electricity", "Managed assets- electricity"):
        return "generation (location-based grid average)"
    if level1 in ("Waste disposal",):
        return "disposal / end-of-life treatment"
    if level1 in ("Water treatment",):
        return "wastewater treatment"
    if level1 in ("Water supply",):
        return "supply (abstraction & distribution)"
    return "combustion / direct activity (tank-to-wheel or point-of-use)"


def main():
    wb = openpyxl.load_workbook(SRC_PATH, read_only=True, data_only=True)
    ws = wb["Factors by Category"]
    rows = ws.iter_rows(min_row=7, values_only=True)

    records = []
    skipped_out_of_scope = 0
    skipped_no_value = 0

    for r in rows:
        row_id, scope_label, l1, l2, l3, l4, col_text, uom, ghg_unit, value = r
        if row_id is None:
            continue
        if value is None:
            skipped_no_value += 1
            continue
        if not scope_label or scope_label not in ("Scope 1", "Scope 2", "Scope 3"):
            skipped_out_of_scope += 1
            continue

        cat, cat_name, scope_n = category_for(scope_label, l1)
        if scope_n is None:
            skipped_out_of_scope += 1
            continue

        breadcrumb_parts = [p for p in (l1, l2, l3, l4, col_text) if p]
        activity = " — ".join(breadcrumb_parts)
        breadcrumb = " > ".join(breadcrumb_parts)

        rec = {
            "id": slugify(str(row_id)),
            "activity": activity,
            "scope": scope_n,
            "category": cat,
            "category_name": cat_name,
            "method": "activity-based",
            "value": round(float(value), 6),
            "unit_numerator": "kgCO2e",
            "unit_denominator": str(uom),
            "gases": gases_for(str(ghg_unit)),
            "gwp_basis": "IPCC AR5 GWP100",
            "country": "GB",
            "year": YEAR,
            "publication_year": YEAR,
            "organization": ORG,
            "dataset": DATASET,
            "source_url": SOURCE_URL,
            "source_page_or_table": f"Factors by Category — {breadcrumb} [{uom}] — row ID {row_id}",
            "licence": LICENCE,
            "price_year": None,
            "currency_deflator_note": None,
            "boundary": boundary_for(l1 or ""),
            "value_status": "verified",
            "notes": f"GHG measure: {ghg_unit}. Defra category path: {breadcrumb}.",
        }
        records.append(rec)

    print(f"DEFRA: {len(records)} records, {skipped_no_value} skipped (no value), "
          f"{skipped_out_of_scope} skipped (out of scope)")

    ids = [r["id"] for r in records]
    assert len(ids) == len(set(ids)), "duplicate ids in DEFRA output!"

    import os
    os.makedirs("out", exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(records, f, ensure_ascii=False)
    print("wrote", OUT_PATH)


if __name__ == "__main__":
    main()
