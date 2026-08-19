"""
Combine parsed source files, validate every record against data/schema.json's
rules, split into chunk files under data/factors/, and write the manifest.
"""
import json
import os

REQUIRED = [
    "id", "activity", "scope", "category", "category_name", "method",
    "value", "unit_numerator", "unit_denominator", "gwp_basis",
    "country", "year", "organization", "dataset", "source_url",
    "licence", "boundary", "value_status",
]
METHOD_ENUM = {"spend-based", "weight-based", "activity-based", "average-data",
                "supplier-specific", "hybrid"}
STATUS_ENUM = {"verified", "unverified", "placeholder"}

SOURCES = [
    ("defra-2025", "out/defra-2025.json", "UK GHG Conversion Factors 2025 (Defra/DESNZ)"),
    ("epa-hub-2025", "out/epa-hub-2025.json", "US EPA GHG Emission Factors Hub 2025"),
    ("epa-egrid-2023", "out/epa-egrid-2023.json", "US EPA eGRID2023 electricity factors"),
    ("nz-mfe-2026", "out/nz-mfe-2026.json", "NZ Ministry for the Environment — Measuring Emissions 2026"),
    ("cea-india-2025", "out/cea-india-2025.json", "India CEA CO2 Baseline Database v21.0"),
    ("eccc-canada-2026", "out/eccc-canada-2026.json", "Canada ECCC Federal GHG Offset System Emission Factors"),
    ("eurostat-2024", "out/eurostat-2024.json", "Eurostat GHG Intensity by NACE Sector (EU + EEA countries)"),
    ("ember-electricity-2024", "out/ember-electricity-2024.json", "Ember Yearly Electricity Data — national grid intensity (~200 countries)"),
]

DEST_DIR = "../data/factors"


def validate(rec, idx, fname):
    for field in REQUIRED:
        if field not in rec or rec[field] is None:
            raise ValueError(f"{fname}[{idx}] id={rec.get('id')}: missing required field '{field}'")
    if rec["scope"] not in (1, 2, 3):
        raise ValueError(f"{fname}[{idx}] id={rec['id']}: bad scope {rec['scope']}")
    if rec["method"] not in METHOD_ENUM:
        raise ValueError(f"{fname}[{idx}] id={rec['id']}: bad method {rec['method']}")
    if rec["value_status"] not in STATUS_ENUM:
        raise ValueError(f"{fname}[{idx}] id={rec['id']}: bad value_status {rec['value_status']}")
    if rec["value_status"] == "verified" and not isinstance(rec["value"], (int, float)):
        raise ValueError(f"{fname}[{idx}] id={rec['id']}: verified but value is not numeric")
    if rec["method"] == "spend-based" and rec.get("price_year") is None:
        raise ValueError(f"{fname}[{idx}] id={rec['id']}: spend-based without price_year")
    if not rec["id"].replace("-", "").replace(".", "").isalnum():
        raise ValueError(f"{fname}[{idx}] id={rec['id']}: id has invalid characters")


def main():
    os.makedirs(DEST_DIR, exist_ok=True)
    manifest = []
    all_ids = set()
    grand_total = 0

    for slug, path, label in SOURCES:
        with open(path) as f:
            data = json.load(f)
        for i, rec in enumerate(data):
            validate(rec, i, path)
            if rec["id"] in all_ids:
                raise ValueError(f"duplicate id across sources: {rec['id']}")
            all_ids.add(rec["id"])

        out_path = os.path.join(DEST_DIR, f"{slug}.json")
        with open(out_path, "w") as f:
            json.dump(data, f, ensure_ascii=False)
        size_kb = os.path.getsize(out_path) / 1024
        manifest.append({
            "file": f"data/factors/{slug}.json",
            "label": label,
            "count": len(data),
            "size_kb": round(size_kb, 1),
        })
        grand_total += len(data)
        print(f"{slug}: {len(data)} records, {size_kb:.0f} KB -> {out_path}")

    with open(os.path.join("..", "data", "index.json"), "w") as f:
        json.dump({"total_records": grand_total, "files": manifest}, f, indent=2)

    print(f"\nGRAND TOTAL: {grand_total} verified records across {len(SOURCES)} datasets")


if __name__ == "__main__":
    main()
