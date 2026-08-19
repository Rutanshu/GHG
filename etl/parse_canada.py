"""
Parse Environment and Climate Change Canada's 'Emission factors and
reference values' page (Federal Greenhouse Gas Offset System) into
normalized emission-factor records: natural gas (CO2, CH4, N2O) by
province/territory, NGL and refined-petroleum-product factors, provincial
electricity consumption intensity, and biogas N2O factors.

Source: https://www.canada.ca/en/environment-climate-change/services/climate-change/pricing-pollution-how-it-will-work/output-based-pricing-system/federal-greenhouse-gas-offset-system/emission-factors-reference-values.html
File used: eccc-offset-emission-factors-2026.html (saved copy of the live page)
"""
import json
import re
import os
from bs4 import BeautifulSoup

SRC_PATH = "raw/eccc-offset-emission-factors-2026.html"
OUT_PATH = "out/eccc-canada-2026.json"

SOURCE_URL = "https://www.canada.ca/en/environment-climate-change/services/climate-change/pricing-pollution-how-it-will-work/output-based-pricing-system/federal-greenhouse-gas-offset-system/emission-factors-reference-values.html"
ORG = "Environment and Climate Change Canada (ECCC)"
DATASET = "Federal Greenhouse Gas Offset System — Emission Factors and Reference Values"
LICENCE = "Open Government Licence — Canada"
PUB_YEAR = 2025

records = []
_seen_ids = set()


def add(rid, activity, scope, cat, cat_name, value, unit_num, unit_denom, gas,
        region, year, source_page, notes=None):
    base = "eccc-canada-2026-" + re.sub(r"[^a-z0-9]+", "-", rid.lower()).strip("-")
    fid, n = base, 2
    while fid in _seen_ids:
        fid = f"{base}-{n}"
        n += 1
    _seen_ids.add(fid)
    records.append({
        "id": fid,
        "activity": activity,
        "scope": scope,
        "category": cat,
        "category_name": cat_name,
        "method": "activity-based",
        "value": round(float(value), 6),
        "unit_numerator": unit_num,
        "unit_denominator": unit_denom,
        "gases": [gas] if gas != "CO2e" else ["CO2", "CH4", "N2O"],
        "gwp_basis": "IPCC AR5 GWP100",
        "country": "CA",
        "region": region,
        "year": year,
        "publication_year": PUB_YEAR,
        "organization": ORG,
        "dataset": DATASET,
        "source_url": SOURCE_URL,
        "source_page_or_table": source_page,
        "licence": LICENCE,
        "price_year": None,
        "currency_deflator_note": None,
        "boundary": "combustion (direct activity)" if scope == 1 else "generation (location-based grid average)",
        "value_status": "verified",
        "notes": notes,
    })


NBSP = "\xa0"


def parse_cell(text):
    """Return (value, unit_override_or_None). Some cells embed a per-row unit
    override, e.g. '27.5 g/m3Footnote17' for a fuel measured by volume of gas
    rather than the table's default per-litre basis."""
    t = re.sub(r"Footnote\d+", "", text).strip()
    t = t.replace(NBSP, " ")
    if t in ("-", "", "–"):
        return None, None
    m = re.match(r"^(-?[\d,\s]+(?:\.\d+)?)\s*(g/m3|g/L)?$", t)
    if not m:
        return None, None
    value = float(m.group(1).replace(" ", "").replace(",", ""))
    unit_override = "m3 fuel gas" if m.group(2) == "g/m3" else ("L fuel" if m.group(2) == "g/L" else None)
    return value, unit_override


def num(text):
    v, _ = parse_cell(text)
    return v


def clean_header(text):
    return re.sub(r"Footnote\d+", "", text).strip().rstrip("*")


def table_rows(table):
    trs = table.find_all("tr")
    header = [clean_header(c.get_text(strip=True)) for c in trs[0].find_all(["th", "td"])]
    data = []
    for tr in trs[1:]:
        cells = [clean_header(c.get_text(strip=True)) for c in tr.find_all(["th", "td"])]
        if cells:
            data.append(cells)
    return header, data


def natural_gas_co2(table, years, table_label):
    header, rows = table_rows(table)
    for row in rows:
        province = row[0]
        for col_idx, sub in ((1, "marketable"), (2, "non-marketable")):
            if col_idx >= len(row):
                continue
            val = num(row[col_idx])
            if val is None:
                continue
            for year in years:
                add(f"ng-co2-{province}-{sub}-{year}",
                    f"Natural gas combustion — {province} ({sub}) — CO2", 1, "1", "Scope 1 direct",
                    val, "gCO2", "m3 natural gas", "CO2", province, year,
                    f"{table_label} — {province}, {sub}")


def natural_gas_ch4n2o(table, years, table_label):
    header, rows = table_rows(table)
    for row in rows:
        source = row[0]
        for col_idx, gas in ((1, "CH4"), (2, "N2O")):
            if col_idx >= len(row):
                continue
            val = num(row[col_idx])
            if val is None:
                continue
            for year in years:
                add(f"ng-{gas}-{source}-{year}",
                    f"Natural gas combustion — {source} — {gas}", 1, "1", "Scope 1 direct",
                    val, f"g{gas}", "m3 natural gas", gas, "Canada (national)", year,
                    f"{table_label} — source category '{source}'")


def fuel_ghg_table(table, years, table_label, denom):
    header, rows = table_rows(table)
    for row in rows:
        fuel = row[0]
        for col_idx, gas in ((1, "CO2"), (2, "CH4"), (3, "N2O")):
            if col_idx >= len(row):
                continue
            val, unit_override = parse_cell(row[col_idx])
            if val is None:
                continue
            row_denom = unit_override or denom
            note = f"{table_label} — {fuel}"
            if unit_override:
                note += f" (unit for this fuel is per {unit_override}, not per {denom})"
            for year in years:
                add(f"fuel-{fuel}-{gas}-{year}",
                    f"Fuel combustion — {fuel} — {gas}", 1, "1", "Scope 1 direct",
                    val, f"g{gas}", row_denom, gas, "Canada (national)", year, note)


def electricity_table(table, years, table_label):
    header, rows = table_rows(table)
    for row in rows:
        province = row[0]
        if len(row) < 2:
            continue
        val = num(row[1])
        if val is None:
            continue
        for year in years:
            add(f"elec-{province}-{year}", f"Purchased electricity — {province} — consumption intensity",
                2, "2", "Scope 2 purchased energy", val, "gCO2e", "kWh", "CO2e",
                province, year, f"{table_label} — {province}")


def enteric_ym_table(table, table_label):
    header, rows = table_rows(table)
    for row in rows:
        diet, val = row[0], num(row[1])
        if val is None:
            continue
        add(f"enteric-ym-{diet[:60]}", f"Enteric fermentation — CH4 conversion factor (Ym) — {diet}",
            1, "1", "Scope 1 direct", val, "fraction", "gross energy intake (GE)", "CH4",
            "Canada (national)", 2025, f"{table_label} — {diet}",
            notes="Ym: fraction of gross energy intake converted to enteric CH4 (IPCC Tier 2 parameter).")


def lipid_ef_table(table, table_label):
    header, rows = table_rows(table)
    for row in rows:
        lipid, val = row[0], num(row[1])
        if val is None:
            continue
        add(f"lipid-ef-{lipid}", f"Enteric fermentation — supplemented lipid CH4 reduction factor — {lipid}% added",
            1, "1", "Scope 1 direct", val, "multiplier", "baseline Ym", "CH4",
            "Canada (national)", 2025, f"{table_label} — {lipid}% supplemented lipid",
            notes="Multiplier applied to the baseline Ym conversion factor for diets with added lipid.")


def manure_table(table, table_label):
    header, rows = table_rows(table)
    for row in rows:
        system = row[0]
        cols = [("MCF", 1, "fraction", "max CH4 producing capacity (VS basis)", "CH4"),
                ("EFMS direct N2O", 2, "kgN2O-N", "kg N excreted", "N2O"),
                ("Frac_volatilize", 3, "fraction", "N excreted", "N2O"),
                ("Frac_leach", 4, "fraction", "N excreted", "N2O")]
        for label, ci, unit_num, unit_denom, gas in cols:
            if ci >= len(row):
                continue
            val = num(row[ci])
            if val is None:
                continue
            add(f"manure-{system}-{label}", f"Manure management — {system} — {label}",
                1, "1", "Scope 1 direct", val, unit_num, unit_denom, gas,
                "Canada (national)", 2025, f"{table_label} — {system}, {label}")


def ecozone_efv_table(table, table_label):
    header, rows = table_rows(table)
    for row in rows:
        zone, val = row[0], num(row[1])
        if val is None:
            continue
        add(f"efv-{zone}", f"Manure management — indirect N2O from volatilization — {zone}",
            1, "1", "Scope 1 direct", val, "kgN2O-N", "kg N volatilized", "N2O",
            zone, 2025, f"{table_label} — {zone}")


def biogas_table(table, years, table_label):
    header, rows = table_rows(table)
    for row in rows:
        desc = row[0]
        if len(row) < 2:
            continue
        val = num(row[1])
        if val is None:
            continue
        for year in years:
            add(f"biogas-n2o-{desc}-{year}", f"Biogas combustion — {desc} — N2O", 1, "1", "Scope 1 direct",
                val, "kgN2O", "t CH4 combusted", "N2O", "Canada (national)", year,
                f"{table_label} — {desc}")


def main():
    with open(SRC_PATH) as f:
        soup = BeautifulSoup(f.read(), "html.parser")
    tables = soup.find_all("table")

    natural_gas_co2(tables[1], [2023, 2024], "Table 1.1 (natural gas CO2)")
    natural_gas_co2(tables[2], [2025], "Table 1.2 (natural gas CO2)")
    natural_gas_co2(tables[3], [2026], "Table 1.3 (natural gas CO2)")

    natural_gas_ch4n2o(tables[4], [2023, 2024], "Table 2.1 (natural gas CH4/N2O)")
    natural_gas_ch4n2o(tables[5], [2025], "Table 2.2 (natural gas CH4/N2O)")
    natural_gas_ch4n2o(tables[6], [2026], "Table 2.3 (natural gas CH4/N2O)")

    fuel_ghg_table(tables[7], [2023, 2024], "Table 3.1 (natural gas liquids)", "L fuel")
    fuel_ghg_table(tables[8], [2025], "Table 3.2 (natural gas liquids)", "L fuel")
    fuel_ghg_table(tables[9], [2026], "Table 3.3 (natural gas liquids)", "L fuel")

    fuel_ghg_table(tables[10], [2023, 2024], "Table 4.1 (refined petroleum products)", "L fuel")
    fuel_ghg_table(tables[11], [2025], "Table 4.2 (refined petroleum products)", "L fuel")
    fuel_ghg_table(tables[12], [2026], "Table 4.3 (refined petroleum products)", "L fuel")

    electricity_table(tables[13], [2023, 2024], "Table 5.1 (electricity consumption intensity)")
    electricity_table(tables[14], [2025], "Table 5.2 (electricity consumption intensity)")
    electricity_table(tables[15], [2026], "Table 5.3 (electricity consumption intensity)")

    biogas_table(tables[16], [2023, 2024], "Table 6.1 (biogas N2O)")
    biogas_table(tables[17], [2025], "Table 6.2 (biogas N2O)")
    biogas_table(tables[18], [2026], "Table 6.3 (biogas N2O)")

    enteric_ym_table(tables[21], "Table 9 (enteric CH4 conversion factors by diet)")
    lipid_ef_table(tables[22], "Table 10 (supplemented lipid CH4 reduction factor)")
    manure_table(tables[23], "Table 11 (manure management CH4/N2O factors by storage system)")
    ecozone_efv_table(tables[24], "Table 12 (indirect N2O from manure volatilization by ecozone)")

    print(f"ECCC Canada: {len(records)} records")
    ids = [r["id"] for r in records]
    assert len(ids) == len(set(ids)), "duplicate ids in Canada output!"

    os.makedirs("out", exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(records, f, ensure_ascii=False)
    print("wrote", OUT_PATH)


if __name__ == "__main__":
    main()
