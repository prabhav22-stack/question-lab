import csv
from pathlib import Path

ROOT = Path("D:/Stuff/ExamForge")
CSV_PATH = ROOT / "engine_v31_experiment/pyq_extraction/outputs/locked_units_clustered_pyqs.csv"

with open(CSV_PATH, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

fixed_count = 0
for r in rows:
    fmt = r["format_type"]
    raw_m = r["marks"]
    if not raw_m or raw_m.strip() == "":
        r["marks"] = "10" if fmt == "SPLIT_10M" else "20"
        fixed_count += 1
    else:
        try:
            clean_m = str(int(float(raw_m)))
            if clean_m != raw_m:
                r["marks"] = clean_m
                fixed_count += 1
        except:
            r["marks"] = "10" if fmt == "SPLIT_10M" else "20"
            fixed_count += 1

with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Successfully normalized marks for {fixed_count} records in {CSV_PATH}")
