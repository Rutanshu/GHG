"""
Parse EPA eGRID2023 (rev2) electricity emission-rate tables — subregion,
state, NERC-region, and national level — into normalized emission-factor
records. Only greenhouse-gas rate columns (CO2, CH4, N2O, CO2-equivalent)
are kept; NOx/SO2/Hg (criteria pollutants, not GHGs) are excluded.

Source: https://www.epa.gov/egrid
File used: egrid2023_data_rev2.xlsx
"""
import json
import re
import os
import openpyxl

SRC_PATH = "raw/egrid2023_data_rev2.xlsx"
OUT_PATH = "out/epa-egrid-2023.json"

SOURCE_URL = "https://www.epa.gov/egrid/download-data"
ORG = "US Environmental Protection Agency (EPA)"
DATASET = "eGRID2023 (Revision 2)"
LICENCE = "US Government work — public domain"
YEAR = 2023
PUB_YEAR = 2025

GAS_MAP = {"CO2 equivalent": "CO2e", "CO2": "CO2", "CH4": "CH4", "N2O": "N2O"}
GAS_RE = re.compile(r"\b(CO2 equivalent|CO2|CH4|N2O)\b")
UNIT_RE = re.compile(r"\(([^)]+)\)\s*$")

US_STATES = {
    "AK": "Alaska", "AL": "Alabama", "AR": "Arkansas", "AZ": "Arizona", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DC": "District of Columbia", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "IA": "Iowa", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "MA": "Massachusetts", "MD": "Maryland", "ME": "Maine", "MI": "Michigan", "MN": "Minnesota",
    "MO": "Missouri", "MS": "Mississippi", "MT": "Montana", "NC": "North Carolina",
    "ND": "North Dakota", "NE": "Nebraska", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NV": "Nevada", "NY": "New York", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "PR": "Puerto Rico", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VA": "Virginia", "VT": "Vermont", "WA": "Washington", "WI": "Wisconsin",
    "WV": "West Virginia", "WY": "Wyoming",
}

records = []
_seen_ids = set()


def add(rid, activity, region_kind, region_code, region_name, value, unit_num, unit_denom,
        gas, table_label):
    base = "epa-egrid-2023-" + re.sub(r"[^a-z0-9]+", "-", rid.lower()).strip("-")
    fid = base
    n = 2
    while fid in _seen_ids:
        fid = f"{base}-{n}"
        n += 1
    _seen_ids.add(fid)
    records.append({
        "id": fid,
        "activity": activity,
        "scope": 2,
        "category": "2",
        "category_name": "Scope 2 purchased energy",
        "method": "activity-based",
        "value": round(float(value), 6),
        "unit_numerator": unit_num,
        "unit_denominator": unit_denom,
        "gases": [gas] if gas != "CO2e" else ["CO2", "CH4", "N2O"],
        "gwp_basis": "IPCC AR5 GWP100",
        "country": "US",
        "region": region_name,
        "year": YEAR,
        "publication_year": PUB_YEAR,
        "organization": ORG,
        "dataset": DATASET,
        "source_url": SOURCE_URL,
        "source_page_or_table": table_label,
        "licence": LICENCE,
        "price_year": None,
        "currency_deflator_note": None,
        "boundary": "generation (location-based grid average electricity)",
        "value_status": "verified",
        "notes": f"eGRID {region_kind} = {region_code}.",
    })


def factor_columns(header0):
    """Return list of (idx, gas, basis_label, unit) for GHG rate columns."""
    out = []
    for idx, h in enumerate(header0):
        if not h or "emission rate" not in str(h).lower():
            continue
        gm = GAS_RE.search(str(h))
        if not gm or gm.group(1) not in GAS_MAP:
            continue
        gas = GAS_MAP[gm.group(1)]
        um = UNIT_RE.search(str(h))
        unit = um.group(1) if um else "unit"
        basis = str(h)
        out.append((idx, gas, basis, unit))
    return out


def unit_split(unit_text):
    # e.g. "lb/MWh" -> ("lbCO2","MWh")
    parts = unit_text.split("/")
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return unit_text, ""


def parse_sheet(sheet, id_col, name_col, region_kind, prefix, name_lookup=None):
    wb = openpyxl.load_workbook(SRC_PATH, read_only=True, data_only=True)
    ws = wb[sheet]
    rows = list(ws.iter_rows(min_row=1, values_only=True))
    header0 = rows[0]
    cols = factor_columns(header0)
    n = 0
    for r in rows[2:]:
        if r[0] is None:
            continue
        code = str(r[id_col]).strip() if id_col is not None else "US"
        name = str(r[name_col]).strip() if name_col is not None else (name_lookup.get(code, code) if name_lookup else code)
        for idx, gas, basis, unit in cols:
            val = r[idx]
            if val in (None, "--", "NA"):
                continue
            mass_unit, denom = unit_split(unit)
            unit_num = mass_unit.replace(" ", "") + gas
            basis_clean = re.sub(r"\s*\([^)]*\)\s*$", "", basis).strip()
            activity = f"Purchased electricity — {name} ({region_kind} {code}) — {basis_clean}"
            tbl = f"eGRID2023 {sheet} — {code} — {basis_clean} [{unit}]"
            add(f"{prefix}-{code}-{basis_clean}", activity, region_kind, code, name, val,
                unit_num, denom, gas, tbl)
            n += 1
    print(f"{sheet}: {n} records")


def main():
    parse_sheet("SRL23", id_col=1, name_col=2, region_kind="eGRID subregion", prefix="sr")
    parse_sheet("ST23", id_col=1, name_col=None, region_kind="state", prefix="st",
                name_lookup=US_STATES)
    parse_sheet("NRL23", id_col=1, name_col=2, region_kind="NERC region", prefix="nr")
    parse_sheet("BA23", id_col=1, name_col=2, region_kind="balancing authority", prefix="ba")
    parse_sheet("US23", id_col=None, name_col=None, region_kind="national", prefix="us")

    print(f"eGRID total: {len(records)}")
    ids = [r["id"] for r in records]
    assert len(ids) == len(set(ids)), "duplicate ids in eGRID output!"

    os.makedirs("out", exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(records, f, ensure_ascii=False)
    print("wrote", OUT_PATH)


if __name__ == "__main__":
    main()
