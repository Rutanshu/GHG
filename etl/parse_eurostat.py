"""
Parse Eurostat's 'Air emissions intensities by NACE Rev. 2 activity'
(env_ac_aeint_r2) into normalized spend-based GHG emission-factor records —
grams CO2e per euro of sector output / value-added, for every EU member
state (plus a few EEA/candidate countries Eurostat also reports), by
economic sector, for 2023 and 2024.

Source: https://ec.europa.eu/eurostat/databrowser/view/env_ac_aeint_r2/default/table
File used: eurostat-env_ac_aeint_r2-2023-2024.json (official Eurostat REST API,
JSON-stat format, filtered to airpol=GHG, unit=G_EUR_CP, time=2023,2024)
"""
import json
import re
import os

SRC_PATH = "raw/eurostat-env_ac_aeint_r2-2023-2024.json"
OUT_PATH = "out/eurostat-2024.json"

SOURCE_URL = "https://ec.europa.eu/eurostat/databrowser/view/env_ac_aeint_r2/default/table"
ORG = "Eurostat (European Commission) / European Environment Agency (EEA)"
DATASET = "Air emissions intensities by NACE Rev. 2 activity (env_ac_aeint_r2)"
LICENCE = "CC BY 4.0 (Eurostat standard reuse policy)"
PUB_YEAR = 2026

GEO_TO_ISO2 = {"EL": "GR", "UK": "GB"}
NA_ITEM_LABEL = {"P1": "output (revenue)", "B1G": "value added, gross"}

records = []
_seen_ids = set()


def add(rid, activity, value, country, region, year, sector_code, sector_name, na_item, notes):
    base = "eurostat-2024-" + re.sub(r"[^a-z0-9]+", "-", rid.lower()).strip("-")
    fid, n = base, 2
    while fid in _seen_ids:
        fid = f"{base}-{n}"
        n += 1
    _seen_ids.add(fid)
    records.append({
        "id": fid,
        "activity": activity,
        "scope": 3,
        "category": "3.1",
        "category_name": "Purchased goods and services",
        "method": "spend-based",
        "value": round(float(value), 6),
        "unit_numerator": "gCO2e",
        "unit_denominator": "EUR",
        "gases": ["CO2", "CH4", "N2O", "HFC", "PFC", "SF6", "NF3"],
        "gwp_basis": "IPCC AR5 GWP100",
        "country": country,
        "region": region,
        "year": year,
        "publication_year": PUB_YEAR,
        "organization": ORG,
        "dataset": DATASET,
        "source_url": SOURCE_URL,
        "source_page_or_table": f"env_ac_aeint_r2 — nace_r2={sector_code} ({sector_name}), na_item={na_item} ({NA_ITEM_LABEL[na_item]}), unit=G_EUR_CP, geo={country}, time={year}",
        "licence": LICENCE,
        "price_year": year,
        "currency_deflator_note": "Current-price EUR for the stated year — deflate/inflate to your spend's reporting-year EUR before multiplying.",
        "boundary": "economy-wide production-account intensity (national accounts basis, all Scope 1+2+3 of the sector's own operations blended)",
        "value_status": "verified",
        "notes": notes,
    })


def flat_index(indices, sizes):
    idx, mult = 0, 1
    for i in reversed(range(len(sizes))):
        idx += indices[i] * mult
        mult *= sizes[i]
    return idx


def main():
    with open(SRC_PATH) as f:
        d = json.load(f)

    ids = d["id"]
    sizes = d["size"]
    idx_maps = {k: d["dimension"][k]["category"]["index"] for k in ids}
    labels = {k: d["dimension"][k]["category"]["label"] for k in ids}

    nace_items = list(idx_maps["nace_r2"].items())
    na_items = list(idx_maps["na_item"].items())
    geo_items = list(idx_maps["geo"].items())
    time_items = list(idx_maps["time"].items())

    for sector_code, nace_pos in nace_items:
        sector_name = labels["nace_r2"][sector_code]
        for na_item, na_pos in na_items:
            for geo_code, geo_pos in geo_items:
                if geo_code == "EU27_2020":
                    country, region = "EU", "European Union — 27 countries (from 2020), aggregate"
                else:
                    country = GEO_TO_ISO2.get(geo_code, geo_code)
                    region = None
                geo_name = labels["geo"][geo_code]
                for time_code, time_pos in time_items:
                    year = int(time_code)
                    indices = [0, 0, nace_pos, na_pos, 0, geo_pos, time_pos]
                    fi = flat_index(indices, sizes)
                    val = d["value"].get(str(fi))
                    if val is None:
                        continue
                    activity = f"{sector_name} — spend-based GHG intensity ({NA_ITEM_LABEL[na_item]}) — {geo_name}"
                    add(f"{sector_code}-{na_item}-{geo_code}-{time_code}", activity, val, country, region,
                        year, sector_code, sector_name, na_item,
                        notes=f"NACE Rev.2 sector {sector_code}: {sector_name}." + (f" {region}" if region else ""))

    print(f"Eurostat: {len(records)} records")
    rids = [r["id"] for r in records]
    assert len(rids) == len(set(rids)), "duplicate ids in Eurostat output!"

    os.makedirs("out", exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(records, f, ensure_ascii=False)
    print("wrote", OUT_PATH)


if __name__ == "__main__":
    main()
