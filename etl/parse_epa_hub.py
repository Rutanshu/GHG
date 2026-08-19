"""
Parse the US EPA 'GHG Emission Factors Hub' 2025 workbook (a formatted report,
not a tidy data table) into normalized emission-factor records.

Source: https://www.epa.gov/climateleadership/ghg-emission-factors-hub
File used: ghg-emission-factors-hub-2025.xlsx
Tables 1-10 are parsed (combustion, electricity, steam/heat, and the three
Scope 3 category tables). Tables 11-12 are GWP reference tables, not emission
factors, and are intentionally excluded.
"""
import json
import re
import os
import openpyxl

SRC_PATH = "raw/epa-ghg-factors-hub-2025.xlsx"
OUT_PATH = "out/epa-hub-2025.json"

SOURCE_URL = "https://www.epa.gov/climateleadership/ghg-emission-factors-hub"
ORG = "US Environmental Protection Agency (EPA)"
DATASET = "GHG Emission Factors Hub (January 2025)"
LICENCE = "US Government work — public domain"
PUB_YEAR = 2025

records = []
_seen_ids = set()


def add(id_suffix, activity, scope, category, category_name, value, unit_num,
        unit_denom, gases, boundary, table_label, notes=None):
    rid = "epa-hub-2025-" + re.sub(r"[^a-z0-9]+", "-", id_suffix.lower()).strip("-")
    base = rid
    n = 2
    while rid in _seen_ids:
        rid = f"{base}-{n}"
        n += 1
    _seen_ids.add(rid)
    records.append({
        "id": rid,
        "activity": activity,
        "scope": scope,
        "category": category,
        "category_name": category_name,
        "method": "activity-based",
        "value": round(float(value), 6) if value not in (None, "NA") else None,
        "unit_numerator": unit_num,
        "unit_denominator": unit_denom,
        "gases": gases,
        "gwp_basis": "IPCC AR5 GWP100",
        "country": "US",
        "year": 2022,
        "publication_year": PUB_YEAR,
        "organization": ORG,
        "dataset": DATASET,
        "source_url": SOURCE_URL,
        "source_page_or_table": table_label,
        "licence": LICENCE,
        "price_year": None,
        "currency_deflator_note": None,
        "boundary": boundary,
        "value_status": "verified" if value not in (None, "NA") else "unverified",
        "notes": notes,
    })


def clean(s):
    return re.sub(r"\s+", " ", str(s)).strip() if s is not None else None


def load_rows():
    wb = openpyxl.load_workbook(SRC_PATH, read_only=True, data_only=True)
    ws = wb["Emission Factors Hub"]
    return list(ws.iter_rows(min_row=1, values_only=True))


def table1(rows):
    """Stationary Combustion: kg/g per mmBtu AND per mass/volume unit."""
    denom_unit = None
    group = None
    i = 15  # row 16 index0
    while i < 99:
        r = rows[i]
        label, c3, c4, c5, c6, c7, c8, c9 = r[2:10]
        if label and str(label).startswith("Source"):
            break
        if label is None and c3 and "per" in str(c3):
            denom_unit = str(c3).split(" per ")[-1]
            i += 1
            continue
        if label and c3 is None and all(v is None for v in (c4, c5, c6, c7, c8, c9)):
            group = clean(label)
            i += 1
            continue
        if label and (c4 is not None or c9 is not None):
            fuel = clean(label)
            activity = f"Stationary combustion — {group + ' — ' if group else ''}{fuel}"
            tbl_mmbtu = f"Table 1 (Stationary Combustion) — {fuel}, per mmBtu heat input (HHV)"
            if c4 is not None:
                add(f"t1-{fuel}-mmbtu", activity + " (per mmBtu heat input)", 1, "1", "Scope 1 direct",
                    c4, "kgCO2", "mmBtu", ["CO2"], "combustion (per unit heat input, HHV)", tbl_mmbtu)
            if c5 is not None:
                add(f"t1-{fuel}-mmbtu-ch4", activity + " (per mmBtu heat input)", 1, "1", "Scope 1 direct",
                    c5 / 1000.0, "kgCH4", "mmBtu", ["CH4"],
                    "combustion (per unit heat input, HHV)", tbl_mmbtu, notes=f"Source value {c5} g CH4/mmBtu")
            if c6 is not None:
                add(f"t1-{fuel}-mmbtu-n2o", activity + " (per mmBtu heat input)", 1, "1", "Scope 1 direct",
                    c6 / 1000.0, "kgN2O", "mmBtu", ["N2O"],
                    "combustion (per unit heat input, HHV)", tbl_mmbtu, notes=f"Source value {c6} g N2O/mmBtu")
            if denom_unit and c7 is not None:
                tbl_unit = f"Table 1 (Stationary Combustion) — {fuel}, per {denom_unit}"
                add(f"t1-{fuel}-{denom_unit}", activity + f" (per {denom_unit})", 1, "1", "Scope 1 direct",
                    c7, "kgCO2", denom_unit, ["CO2"], "combustion (fuel-use basis)", tbl_unit)
        i += 1


def table2(rows):
    for i in range(103, 113):
        label, val, unit = rows[i][2:5]
        if not label:
            continue
        tbl = f"Table 2 (Mobile Combustion CO2) — {clean(label)}"
        add(f"t2-{label}", f"Mobile combustion CO2 — {clean(label)}", 1, "1", "Scope 1 direct",
            val, "kgCO2", clean(unit), ["CO2"], "combustion (tank-to-wheel)", tbl)


def _forward_fill_table(rows, start, end, ncols):
    """Yield rows with leading label columns forward-filled."""
    cur = [None] * ncols
    for i in range(start, end):
        r = rows[i][2:2 + ncols]
        if r[0] and str(r[0]).startswith(("Source", "Notes")):
            break
        if all(v is None for v in r):
            continue
        merged = list(r)
        for j in range(ncols):
            if merged[j] is None and j < 2:
                merged[j] = cur[j]
        cur = [merged[0], merged[1]] + [None] * (ncols - 2)
        yield merged


def table3(rows):
    for row in _forward_fill_table(rows, 126, 242, 4):
        vt, my, ch4, n2o = row
        if ch4 is None:
            continue
        act = f"Mobile combustion (on-road gasoline) — {clean(vt)}, model year {clean(my)}"
        tbl = f"Table 3 (Mobile CH4/N2O, on-road gasoline) — {clean(vt)} / {clean(my)}"
        add(f"t3-{vt}-{my}-ch4", act, 1, "1", "Scope 1 direct", ch4 / 1000.0, "kgCH4",
            "vehicle-mile", ["CH4"], "combustion (tank-to-wheel)", tbl, notes=f"{ch4} g CH4/vehicle-mile")
        add(f"t3-{vt}-{my}-n2o", act, 1, "1", "Scope 1 direct", n2o / 1000.0, "kgN2O",
            "vehicle-mile", ["N2O"], "combustion (tank-to-wheel)", tbl, notes=f"{n2o} g N2O/vehicle-mile")


def table4(rows):
    for row in _forward_fill_table(rows, 248, 283, 5):
        vt, ft, my, ch4, n2o = row
        if ch4 is None:
            continue
        act = f"Mobile combustion (on-road diesel/alt fuel) — {clean(vt)}, {clean(ft)}" + (f", model year {clean(my)}" if my else "")
        tbl = f"Table 4 (Mobile CH4/N2O, diesel & alt-fuel) — {clean(vt)} / {clean(ft)} / {clean(my)}"
        add(f"t4-{vt}-{ft}-{my}-ch4", act, 1, "1", "Scope 1 direct", ch4 / 1000.0, "kgCH4",
            "vehicle-mile", ["CH4"], "combustion (tank-to-wheel)", tbl, notes=f"{ch4} g CH4/vehicle-mile")
        add(f"t4-{vt}-{ft}-{my}-n2o", act, 1, "1", "Scope 1 direct", n2o / 1000.0, "kgN2O",
            "vehicle-mile", ["N2O"], "combustion (tank-to-wheel)", tbl, notes=f"{n2o} g N2O/vehicle-mile")


def table5(rows):
    for row in _forward_fill_table(rows, 289, 329, 4):
        vt, ft, ch4, n2o = row
        if ch4 is None:
            continue
        act = f"Mobile combustion (non-road) — {clean(vt)}, {clean(ft)}"
        tbl = f"Table 5 (Mobile CH4/N2O, non-road) — {clean(vt)} / {clean(ft)}"
        add(f"t5-{vt}-{ft}-ch4", act, 1, "1", "Scope 1 direct", ch4, "gCH4",
            "gallon", ["CH4"], "combustion (tank-to-wheel)", tbl)
        add(f"t5-{vt}-{ft}-n2o", act, 1, "1", "Scope 1 direct", n2o, "gN2O",
            "gallon", ["N2O"], "combustion (tank-to-wheel)", tbl)


def table6(rows):
    for i in range(338, 406):
        r = rows[i]
        acro, name = r[2], r[3]
        if not acro or str(acro).startswith("Source"):
            if str(acro or "").startswith("Source"):
                break
            continue
        co2t, ch4t, n2ot, co2n, ch4n, n2on = r[4:10]
        tbl = f"Table 6 (Electricity, eGRID subregions) — {acro} {clean(name)}"
        for label, val, gas, unit in (
            ("total output", co2t, "CO2", "lbCO2"), ("total output", ch4t, "CH4", "lbCH4"),
            ("total output", n2ot, "N2O", "lbN2O"), ("non-baseload output", co2n, "CO2", "lbCO2"),
            ("non-baseload output", ch4n, "CH4", "lbCH4"), ("non-baseload output", n2on, "N2O", "lbN2O"),
        ):
            if val is None:
                continue
            add(f"t6-{acro}-{label}-{gas}", f"Purchased electricity — {clean(name)} ({acro}), {label} rate",
                2, "2", "Scope 2 purchased energy", val, unit, "MWh", [gas],
                "generation (location-based grid average, eGRID)", tbl)


def table7(rows):
    r = rows[409]
    co2, ch4, n2o = r[3], r[4], r[5]
    tbl = "Table 7 (Steam and Heat)"
    add("t7-co2", "Purchased steam and heat", 2, "2", "Scope 2 purchased energy", co2, "kgCO2",
        "mmBtu", ["CO2"], "combustion (supplier boiler, tank-to-wheel)", tbl)
    add("t7-ch4", "Purchased steam and heat", 2, "2", "Scope 2 purchased energy", ch4 / 1000.0, "kgCH4",
        "mmBtu", ["CH4"], "combustion (supplier boiler, tank-to-wheel)", tbl, notes=f"{ch4} g CH4/mmBtu")
    add("t7-n2o", "Purchased steam and heat", 2, "2", "Scope 2 purchased energy", n2o / 1000.0, "kgN2O",
        "mmBtu", ["N2O"], "combustion (supplier boiler, tank-to-wheel)", tbl, notes=f"{n2o} g N2O/mmBtu")


def table8(rows):
    for i in range(421, 428):
        vt, co2, ch4, n2o, unit = rows[i][2:7]
        if not vt:
            continue
        tbl = f"Table 8 (Scope 3 Cat 4 & 9: transport & distribution) — {clean(vt)}"
        act = f"Upstream/downstream transportation & distribution — {clean(vt)}"
        add(f"t8-{vt}-co2", act, 3, "3.4", "Upstream transportation and distribution", co2, "kgCO2",
            clean(unit), ["CO2"], "distance-based (also applies to 3.9 downstream)", tbl)
        add(f"t8-{vt}-ch4", act, 3, "3.4", "Upstream transportation and distribution", ch4 / 1000.0, "kgCH4",
            clean(unit), ["CH4"], "distance-based (also applies to 3.9 downstream)", tbl, notes=f"{ch4} g CH4/{unit}")
        add(f"t8-{vt}-n2o", act, 3, "3.4", "Upstream transportation and distribution", n2o / 1000.0, "kgN2O",
            clean(unit), ["N2O"], "distance-based (also applies to 3.9 downstream)", tbl, notes=f"{n2o} g N2O/{unit}")


def table9(rows):
    header = rows[434][2:9]
    methods = [clean(h) for h in header[1:] if h]
    for i in range(435, 500):
        r = rows[i]
        mat = r[2]
        if not mat:
            continue
        if str(mat).startswith(("Source", "Notes")):
            break
        vals = r[3:9]
        for method, val in zip(methods, vals):
            if val in (None, "NA"):
                continue
            method_clean = re.sub(r"[A-Z]$", "", method).strip()
            tbl = f"Table 9 (Scope 3 Cat 5 & 12: waste) — {clean(mat)} / {method_clean}"
            add(f"t9-{mat}-{method_clean}", f"Waste generated in operations — {clean(mat)}, {method_clean.lower()}",
                3, "3.5", "Waste generated in operations", val, "tCO2e", "short ton material", ["CO2", "CH4", "N2O"],
                "end-of-life treatment (also applies to 3.12 end-of-life of sold products)", tbl)


def table10(rows):
    for i in range(503, 516):
        vt, co2, ch4, n2o, unit = rows[i][2:7]
        if not vt or str(vt).startswith("Source"):
            continue
        vt_clean = re.sub(r"[A-Z]$", "", clean(vt)).strip()
        tbl = f"Table 10 (Scope 3 Cat 6 & 7: business travel & commuting) — {vt_clean}"
        act = f"Business travel / employee commuting — {vt_clean}"
        add(f"t10-{vt}-co2", act, 3, "3.6", "Business travel", co2, "kgCO2", clean(unit),
            ["CO2"], "distance-based (also applies to 3.7 employee commuting)", tbl)
        add(f"t10-{vt}-ch4", act, 3, "3.6", "Business travel", ch4 / 1000.0, "kgCH4", clean(unit),
            ["CH4"], "distance-based (also applies to 3.7 employee commuting)", tbl, notes=f"{ch4} g CH4/{unit}")
        add(f"t10-{vt}-n2o", act, 3, "3.6", "Business travel", n2o / 1000.0, "kgN2O", clean(unit),
            ["N2O"], "distance-based (also applies to 3.7 employee commuting)", tbl, notes=f"{n2o} g N2O/{unit}")


def main():
    rows = load_rows()
    table1(rows)
    table2(rows)
    table3(rows)
    table4(rows)
    table5(rows)
    table6(rows)
    table7(rows)
    table8(rows)
    table9(rows)
    table10(rows)

    good = [r for r in records if r["value"] is not None]
    print(f"EPA Hub: {len(good)} records with values ({len(records)} attempted)")

    ids = [r["id"] for r in good]
    assert len(ids) == len(set(ids)), "duplicate ids in EPA hub output!"

    os.makedirs("out", exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(good, f, ensure_ascii=False)
    print("wrote", OUT_PATH)


if __name__ == "__main__":
    main()
