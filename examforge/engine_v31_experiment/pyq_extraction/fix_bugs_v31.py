"""
Fix 1: Deduplicate Max Weber in MPA011-U01+U02_C01
Fix 2: Expand 3 thin 20M answers via Groq (targeting 500+ words)
Fix 3: Clean 3 truncated cluster titles via Groq
"""
import os, sys, json, re, time
from pathlib import Path

ROOT = Path("D:/Stuff/ExamForge")
sys.path.append(str(ROOT / "engine_v31_experiment/pyq_extraction"))
import groq_assistant
import ebook_extractor

MA_PATH = ROOT / "engine_v31_experiment/pyq_extraction/outputs/model_answers.json"
CSV_PATH = ROOT / "engine_v31_experiment/pyq_extraction/outputs/locked_units_clustered_pyqs.csv"

model_answers = json.loads(MA_PATH.read_text(encoding="utf-8"))

# ======================================================
# FIX 1: Deduplicate Max Weber
# ======================================================
print("=== FIX 1: Deduplicating Max Weber ===")
cid = "MPA011-U01+U02_C01"
thinkers = model_answers[cid]["structured_data"]["key_thinkers_cited"]
print(f"  Before: {thinkers}")
deduped = list(dict.fromkeys(thinkers))  # preserve order, remove dups
model_answers[cid]["structured_data"]["key_thinkers_cited"] = deduped
print(f"  After:  {deduped}")
print("  DONE")

# ======================================================
# FIX 2: Expand 3 thin 20M answers
# ======================================================
THIN_TARGETS = {
    "MPA011-U12_C01": {"unit_nums": [12], "course": "MPA-011"},
    "MPA011-U19_C01": {"unit_nums": [19], "course": "MPA-011"},
    "MPA014-U01_C01": {"unit_nums": [1],  "course": "MPA-014"},
}

print("\n=== FIX 2: Expanding thin 20M model answers ===")

for cid, meta in THIN_TARGETS.items():
    entry = model_answers[cid]
    sd = entry["structured_data"]
    old_text = (sd.get("introduction","") + " " +
                " ".join(b["content"] for b in sd.get("body_sections",[])) + " " +
                sd.get("critical_evaluation","") + " " +
                sd.get("conclusion",""))
    old_wc = len(old_text.split())
    print(f"\n  [{cid}] Current: {old_wc} words. Expanding to 500+...")

    u_nums = meta["unit_nums"]
    c_code = meta["course"]
    ebook_excerpt = ebook_extractor.extract_unit_text(c_code, u_nums, max_chars=3000)

    rep_q = entry["representative_question"]
    u_title = entry["unit_title"]
    c_title = entry["cluster_title"]
    fmt = entry["format"]
    marks = entry["marks"]
    thinkers_cited = sd.get("key_thinkers_cited", [])

    # Build the existing answer for reference
    existing_body = "\n".join(
        f"[{b['heading']}]: {b['content']}" for b in sd.get("body_sections", [])
    )
    existing_summary = f"Introduction: {sd.get('introduction','')[:300]}...\nBody: {existing_body[:600]}...\nConclusion: {sd.get('conclusion','')[:200]}..."

    prompt = f"""You are a senior IGNOU Public Administration professor EXPANDING and IMPROVING an existing model answer.

Course: {c_code}
Unit: {u_title}
Theme: {c_title}
Question Format: FULL_20M (20 Marks — requires ~500-600 words MINIMUM)
Exam Question: "{rep_q}"

EXISTING ANSWER (only {old_wc} words — NEEDS EXPANSION):
{existing_summary}

OFFICIAL IGNOU EBOOK EXCERPT:
\"\"\"{ebook_excerpt[:3000]}\"\"\"

INSTRUCTIONS:
1. Rewrite the FULL answer from scratch targeting 520-580 words total.
2. Keep all thinkers already cited: {thinkers_cited}
3. Add at least 2 more substantive academic points in body sections.
4. Keep the same academic tone; ground everything in IGNOU material.
5. Each body section must have at least 80 words of content.
6. Return ONLY valid JSON in this exact structure:

{{
    "question": "{rep_q.replace('"', "'")}",
    "format_and_marks": "FULL_20M | 20 Marks",
    "target_word_count": "520-580 words",
    "introduction": "...",
    "body_sections": [
        {{"heading": "...", "content": "..."}},
        {{"heading": "...", "content": "..."}},
        {{"heading": "...", "content": "..."}},
        {{"heading": "...", "content": "..."}}
    ],
    "critical_evaluation": "...",
    "conclusion": "...",
    "key_thinkers_cited": [...]
}}"""

    messages = [
        {"role": "system", "content": "You are an expert IGNOU examinations professor. Output strict JSON only. Minimum 520 words total."},
        {"role": "user", "content": prompt}
    ]

    max_retries = 5
    res = None
    for attempt in range(max_retries):
        res, is_cached = groq_assistant.call_groq_api(messages, model=groq_assistant.PRIMARY_MODEL, temperature=0.15)
        if isinstance(res, dict) and res.get("status") == "FAILED" and "429" in str(res.get("error", "")):
            wait = (attempt + 1) * 8
            print(f"    Rate limited. Backing off {wait}s...")
            time.sleep(wait)
        else:
            break

    if not isinstance(res, dict) or not res.get("introduction"):
        print(f"    WARNING: Groq failed for {cid}: {res}")
        time.sleep(3)
        continue

    # Verify word count
    new_text = (res.get("introduction","") + " " +
                " ".join(b.get("content","") for b in res.get("body_sections",[])) + " " +
                res.get("critical_evaluation","") + " " +
                res.get("conclusion",""))
    new_wc = len(new_text.split())
    print(f"    New word count: {new_wc}")

    if new_wc < 420:
        print(f"    WARNING: Still thin ({new_wc}w). Keeping expanded version anyway.")

    # Update model_answers
    model_answers[cid]["structured_data"] = res

    # Rebuild HTML
    intro = res.get("introduction", "")
    body_parts = []
    for sec in res.get("body_sections", []):
        h = sec.get("heading", "")
        c = sec.get("content", "")
        body_parts.append(f"<b>{h}</b><br/>{c}")
    body_full = "<br/><br/>".join(body_parts)
    eval_txt = res.get("critical_evaluation", "")
    concl = res.get("conclusion", "")
    full_html = f"<b>Introduction:</b><br/>{intro}<br/><br/>{body_full}<br/><br/><b>Critical Evaluation & Administrative Relevance:</b><br/>{eval_txt}<br/><br/><b>Conclusion:</b><br/>{concl}"
    model_answers[cid]["full_model_answer_html"] = full_html

    MA_PATH.write_text(json.dumps(model_answers, indent=2), encoding="utf-8")
    print(f"    Saved {cid} ({new_wc} words). ✓")
    time.sleep(2.5)

# ======================================================
# FIX 3: Clean 3 truncated cluster titles
# ======================================================
import csv

TRUNCATED_CLUSTERS = {
    "MPA013-U07_C01": "Contextual Uses of Governance and Its Administrative Significance",
    "MPA014-U01_C01": "The Significance and Evolution of Human Resource Management",
    "MPA014-U15_C01": "Total Quality Management (TQM): Concept, Principles and Practice",
}

print("\n=== FIX 3: Fixing truncated cluster titles in CSV ===")

rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
fieldnames = rows[0].keys() if rows else []

changes = 0
for row in rows:
    if row["cluster_id"] in TRUNCATED_CLUSTERS:
        old = row["cluster_title"]
        new = TRUNCATED_CLUSTERS[row["cluster_id"]]
        if old != new:
            row["cluster_title"] = new
            changes += 1

print(f"  CSV rows updated: {changes}")

with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

# Also update model_answers cluster_title fields
for cid, new_title in TRUNCATED_CLUSTERS.items():
    if cid in model_answers:
        old = model_answers[cid].get("cluster_title", "")
        model_answers[cid]["cluster_title"] = new_title
        print(f"  model_answers[{cid}]: '{old}' -> '{new_title}'")

MA_PATH.write_text(json.dumps(model_answers, indent=2), encoding="utf-8")
print("  DONE - titles fixed in CSV and model_answers.json")

# ======================================================
# FINAL WORD COUNT VERIFICATION
# ======================================================
print("\n=== FINAL VERIFICATION: Word counts for fixed answers ===")
ma_fresh = json.loads(MA_PATH.read_text(encoding="utf-8"))
for cid in list(THIN_TARGETS.keys()) + ["MPA011-U01+U02_C01"]:
    sd = ma_fresh[cid]["structured_data"]
    text = (sd.get("introduction","") + " " +
            " ".join(b.get("content","") for b in sd.get("body_sections",[])) + " " +
            sd.get("critical_evaluation","") + " " +
            sd.get("conclusion",""))
    wc = len(text.split())
    thinkers = sd.get("key_thinkers_cited", [])
    dup_flag = " !! DUP" if len(thinkers) != len(set(thinkers)) else ""
    print(f"  {cid}: {wc} words | thinkers={thinkers}{dup_flag}")

print("\nAll fixes complete!")
