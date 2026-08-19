"""
Parse Ember's 'Yearly Electricity Data' into national grid electricity
emission-intensity records (Scope 2, location-based) covering ~200
countries and economies, including China, Germany, France, Denmark and
essentially every other grid Ember tracks.

Source: https://ember-energy.org/data/yearly-electricity-data/
File used: ember-yearly-electricity-data-new.csv (official public CSV,
'Total generation' row, 'Country or economy' area type, 2023-2024)
"""
import csv
import json
import re
import os
import pycountry

SRC_PATH = "raw/ember-yearly-electricity-data.csv"
OUT_PATH = "out/ember-electricity-2024.json"

SOURCE_URL = "https://ember-energy.org/data/yearly-electricity-data/"
ORG = "Ember (independent energy think tank)"
DATASET = "Yearly Electricity Data — national grid emissions intensity"
LICENCE = "CC BY 4.0"
PUB_YEAR = 2026
YEARS = {"2023", "2024"}

# A few ISO-3 codes Ember uses that pycountry doesn't resolve directly.
ISO3_OVERRIDE = {
    "XKX": "XK",   # Kosovo (user-assigned code, widely used)
    "TWN": "TW",   # Taiwan
}


def iso3_to_iso2(code):
    if code in ISO3_OVERRIDE:
        return ISO3_OVERRIDE[code]
    c = pycountry.countries.get(alpha_3=code)
    return c.alpha_2 if c else None


def main():
    records = []
    seen_ids = set()
    skipped_no_iso = []

    with open(SRC_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Electricity source"] != "Total generation":
                continue
            if row["Area type"] != "Country or economy":
                continue
            if row["Year"] not in YEARS:
                continue
            val = row["Emissions intensity (gCO2e/kWh)"]
            if not val:
                continue
            iso2 = iso3_to_iso2(row["ISO 3 code"])
            if not iso2:
                skipped_no_iso.append(row["Area"])
                continue

            rid = f"ember-2024-{iso2.lower()}-{row['Year']}"
            n = 2
            base = rid
            while rid in seen_ids:
                rid = f"{base}-{n}"
                n += 1
            seen_ids.add(rid)

            records.append({
                "id": rid,
                "activity": f"Purchased electricity — {row['Area']} national grid — location-based intensity",
                "scope": 2,
                "category": "2",
                "category_name": "Scope 2 purchased energy",
                "method": "activity-based",
                "value": round(float(val), 4),
                "unit_numerator": "gCO2e",
                "unit_denominator": "kWh",
                "gases": ["CO2", "CH4", "N2O"],
                "gwp_basis": "IPCC AR5 GWP100",
                "country": iso2,
                "region": None,
                "year": int(row["Year"]),
                "publication_year": PUB_YEAR,
                "organization": ORG,
                "dataset": DATASET,
                "source_url": SOURCE_URL,
                "source_page_or_table": f"Yearly Electricity Data — {row['Area']}, Total generation, {row['Year']}, Emissions intensity (gCO2e/kWh)",
                "licence": LICENCE,
                "price_year": None,
                "currency_deflator_note": None,
                "boundary": "generation (location-based national grid average, all sources blended)",
                "value_status": "verified",
                "notes": f"National total generation {row['Generation (TWh)']} TWh, total power-sector emissions {row['Emissions (MtCO2e)']} MtCO2e in {row['Year']}. Ember compiles this from national statistics, Eurostat, EIA, and utility data — not itself a national government filing.",
            })

    print(f"Ember: {len(records)} records; {len(set(skipped_no_iso))} areas skipped (no ISO2 match): {sorted(set(skipped_no_iso))[:20]}")
    ids = [r["id"] for r in records]
    assert len(ids) == len(set(ids)), "duplicate ids in Ember output!"

    os.makedirs("out", exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(records, f, ensure_ascii=False)
    print("wrote", OUT_PATH)


if __name__ == "__main__":
    main()
