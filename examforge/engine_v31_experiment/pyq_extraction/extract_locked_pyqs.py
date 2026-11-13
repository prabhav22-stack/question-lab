import os
import sys
import csv
import json
import re
from pathlib import Path

ROOT = Path("D:/Stuff/ExamForge")
OUTPUT_DIR = ROOT / "engine_v31_experiment/pyq_extraction/outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Authoritative input paths
FROZEN_PORTFOLIO_PATH = ROOT / "engine_v31_experiment/outputs/december_2026_frozen_portfolio.csv"
CANONICAL_REGISTRY_PATH = ROOT / "shared/canonical_syllabus_registry/unit_registry.csv"
TOPIC_REGISTRY_PATH = ROOT / "shared/canonical_syllabus_registry/topic_registry.csv"
SUBTOPIC_REGISTRY_PATH = ROOT / "shared/canonical_syllabus_registry/subtopic_registry.csv"
FORMAT_AUDIT_PATH = ROOT / "engine_v31_experiment/outputs/question_format_and_marks_audit.csv"

COURSE_QUESTIONS_PATHS = {
    "MPA-011": ROOT / "research/mpa011_forecasting/data/questions_master_v3.csv",
    "MPA-012": ROOT / "research/mpa012_forecasting/data/questions_master_v3.csv",
    "MPA-013": ROOT / "research/mpa013_forecasting/data/questions_master_v3.csv",
    "MPA-014": ROOT / "research/mpa014_forecasting/data/questions_master_v3.csv",
}

def load_canonical_registry():
    units = list(csv.DictReader(open(CANONICAL_REGISTRY_PATH, encoding="utf-8")))
    unit_map = {r["canonical_unit_id"]: r for r in units}
    return units, unit_map

def load_adjusted_portfolio():
    raw_portfolio = list(csv.DictReader(open(FROZEN_PORTFOLIO_PATH, encoding="utf-8")))
    adjusted_portfolio = []
    
    # Track units per course
    for r in raw_portfolio:
        c_code = r["course_code"]
        u_num = int(r["unit_number"])
        role = r["role"]
        sec = r["section"]
        u_id = r["canonical_unit_id"]
        title = r["official_unit_title"]
        
        # Rule 2: MPA-011 combine U01 and U02 into MPA011-U01+U02
        if c_code == "MPA-011":
            if u_num == 2:
                adjusted_portfolio.append({
                    "course_code": "MPA-011",
                    "analytical_unit_id": "MPA011-U01+U02",
                    "canonical_unit_ids": ["MPA011-U01", "MPA011-U02"],
                    "unit_numbers": [1, 2],
                    "official_unit_title": "Relationship between State, Society and Public Administration / Nature of the State",
                    "role": "10_CORE",
                    "section": "Section I",
                    "is_combined": True
                })
            else:
                adjusted_portfolio.append({
                    "course_code": "MPA-011",
                    "analytical_unit_id": u_id,
                    "canonical_unit_ids": [u_id],
                    "unit_numbers": [u_num],
                    "official_unit_title": title,
                    "role": "10_CORE" if role == "10_CORE" else "BUFFER",
                    "section": sec,
                    "is_combined": False
                })
        elif c_code == "MPA-014":
            # Rule 3: MPA-014 promote U06 from Buffer to Full Core (Total Core = 11)
            if u_num == 6:
                adjusted_portfolio.append({
                    "course_code": "MPA-014",
                    "analytical_unit_id": u_id,
                    "canonical_unit_ids": [u_id],
                    "unit_numbers": [u_num],
                    "official_unit_title": title,
                    "role": "10_CORE", # Promoted to Full Core
                    "section": sec,
                    "is_combined": False,
                    "promoted": True
                })
            else:
                adjusted_portfolio.append({
                    "course_code": "MPA-014",
                    "analytical_unit_id": u_id,
                    "canonical_unit_ids": [u_id],
                    "unit_numbers": [u_num],
                    "official_unit_title": title,
                    "role": "10_CORE" if role == "10_CORE" else "BUFFER",
                    "section": sec,
                    "is_combined": False
                })
        else:
            adjusted_portfolio.append({
                "course_code": c_code,
                "analytical_unit_id": u_id,
                "canonical_unit_ids": [u_id],
                "unit_numbers": [u_num],
                "official_unit_title": title,
                "role": "10_CORE" if role == "10_CORE" else "BUFFER",
                "section": sec,
                "is_combined": False
            })
            
    # Check counts
    print("\n--- Portfolio Integrity Check ---")
    for c in ["MPA-011", "MPA-012", "MPA-013", "MPA-014"]:
        c_entries = [p for p in adjusted_portfolio if p["course_code"] == c]
        core_cnt = sum(1 for p in c_entries if p["role"] == "10_CORE")
        buff_cnt = sum(1 for p in c_entries if p["role"] == "BUFFER")
        print(f"{c}: Core Entries = {core_cnt}, Buffers = {buff_cnt}")
    print("---------------------------------\n")
    return adjusted_portfolio

def normalize_session(raw_session, year):
    # E.g. MPA011_2021_JUN -> Jun 2021
    # or Dec 2025 -> Dec 2025
    s = str(raw_session).upper()
    y = str(year)
    if "JUN" in s:
        return f"Jun {y}"
    elif "DEC" in s:
        return f"Dec {y}"
    return f"{s} {y}"

def extract_all_questions(adjusted_portfolio):
    # Load format and marks audit
    audit_data = {}
    if FORMAT_AUDIT_PATH.exists():
        for r in csv.DictReader(open(FORMAT_AUDIT_PATH, encoding="utf-8")):
            # key: (course_code, paper_id, question_number, subpart)
            k = (r["course_code"], r["paper_id"], str(r["question_number"]), r["subpart"].strip())
            audit_data[k] = r
            
    extracted_records = []
    seen_composite_ids = set()
    
    # Unit number to analytical entry map per course
    u_to_entry = {}
    for entry in adjusted_portfolio:
        c = entry["course_code"]
        for un in entry["unit_numbers"]:
            u_to_entry[(c, un)] = entry

    for c_code, q_path in COURSE_QUESTIONS_PATHS.items():
        if not q_path.exists():
            print(f"Warning: {q_path} does not exist!")
            continue
            
        with open(q_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Find unit number
                u_val = row.get("unit") or row.get("current_unit")
                if not u_val:
                    continue
                try:
                    u_num = int(u_val)
                except:
                    continue
                    
                entry = u_to_entry.get((c_code, u_num))
                if not entry:
                    # Not in portfolio
                    continue
                    
                year_val = int(row.get("year", 0))
                paper_id = row.get("paper_id", "")
                q_num = str(row.get("question_number", ""))
                subp = str(row.get("subpart", "")).strip()
                q_text = row.get("question_text", "").strip()
                if not q_text:
                    continue
                    
                # Deduplication composite ID
                # (course_code, paper_id, q_num, subp, question_text_prefix)
                comp_id = (c_code, paper_id, q_num, subp, q_text[:50])
                if comp_id in seen_composite_ids:
                    continue
                seen_composite_ids.add(comp_id)
                
                # Check audit for format and marks
                audit_rec = audit_data.get((c_code, paper_id, q_num, subp))
                if audit_rec:
                    fmt = audit_rec.get("format", "FULL_20M")
                    raw_marks = audit_rec.get("marks")
                else:
                    raw_marks = row.get("marks")
                    fmt = "SPLIT_10M" if raw_marks and float(raw_marks) < 20.0 else "FULL_20M"
                    
                # Cleanly normalize marks to string '20' or '10'
                if not raw_marks or str(raw_marks).strip() == "":
                    marks = "10" if fmt == "SPLIT_10M" else "20"
                else:
                    try:
                        marks = str(int(float(raw_marks)))
                    except:
                        marks = "10" if fmt == "SPLIT_10M" else "20"
                    
                sess_norm = normalize_session(paper_id, year_val)
                sec = row.get("section", "")
                if not sec or sec == "None":
                    sec = entry["section"]
                    
                # Word limit signal
                wl_signal = "UNKNOWN"
                if "500" in q_text:
                    wl_signal = "500 words"
                elif "250" in q_text:
                    wl_signal = "250 words"
                elif fmt == "FULL_20M":
                    wl_signal = "500 words (Standard Essay)"
                elif fmt == "SPLIT_10M":
                    wl_signal = "250 words (Standard Short Note)"
                    
                canonical_uid = f"{c_code.replace('-','')}-U{u_num:02d}"
                
                extracted_records.append({
                    "course_id": c_code,
                    "canonical_unit_id": canonical_uid,
                    "analytical_unit_id": entry["analytical_unit_id"],
                    "unit_title": entry["official_unit_title"],
                    "portfolio_tier": entry["role"],
                    "portfolio_section": entry["section"],
                    "session": sess_norm,
                    "raw_paper_id": paper_id,
                    "exam_year": year_val,
                    "question_number": q_num,
                    "subquestion": subp,
                    "section": sec,
                    "question_text": q_text,
                    "format_type": fmt,
                    "marks": marks,
                    "word_limit_signal": wl_signal,
                    "source_question_id": f"{paper_id}_Q{q_num}{subp}"
                })
                
    print(f"Total extracted question records across locked portfolio: {len(extracted_records)}")
    return extracted_records

if __name__ == "__main__":
    portfolio = load_adjusted_portfolio()
    records = extract_all_questions(portfolio)
