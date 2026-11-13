import os
import sys
import csv
import json
import re
from pathlib import Path

ROOT = Path("D:/Stuff/ExamForge")
sys.path.append(str(ROOT / "engine_v31_experiment/pyq_extraction"))
import groq_assistant

OUTPUT_DIR = ROOT / "engine_v31_experiment/pyq_extraction/outputs"
CSV_PATH = OUTPUT_DIR / "locked_units_clustered_pyqs.csv"
TOPIC_REGISTRY_PATH = ROOT / "shared/canonical_syllabus_registry/topic_registry.csv"

def is_unclean_title(t):
    if not t:
        return True
    if any(x in t for x in ["...", ": “", ": “", "10 Section", "A–197", "Describe the", "Explain the", "Analyse the", "Discuss the", "Highlight the"]):
        return True
    if "&" in t and len(t.split("&")) >= 3: # E.g. "Gandhi & Gandhian & Rti"
        return True
    if re.search(r'^(Rti:|Marx:|Taylor:|Tqm:|Sala:|Bureaucracy:|Civil Society:)', t, re.I):
        return True
    return False

def clean_all_unclean_titles():
    print("Inspecting cluster titles for formatting anomalies...")
    with open(CSV_PATH, encoding="utf-8") as f:
        records = list(csv.DictReader(f))
        
    topics = list(csv.DictReader(open(TOPIC_REGISTRY_PATH, encoding="utf-8")))
    unit_topics = {}
    for t in topics:
        c = t["course_code"]
        try:
            u_num = int(t["unit_number"])
        except:
            continue
        k = (c, u_num)
        if k not in unit_topics:
            unit_topics[k] = []
        unit_topics[k].append(t)
        
    cluster_map = {}
    for r in records:
        cid = r["cluster_id"]
        if cid not in cluster_map:
            cluster_map[cid] = []
        cluster_map[cid].append(r)
        
    unclean_cids = [cid for cid, recs in cluster_map.items() if is_unclean_title(recs[0]["cluster_title"])]
    print(f"Total clusters: {len(cluster_map)} | Clusters requiring title polish: {len(unclean_cids)}")
    
    updated_titles = {}
    for cid in unclean_cids:
        recs = cluster_map[cid]
        sample = recs[0]
        c_code = sample["course_id"]
        a_id = sample["analytical_unit_id"]
        u_title = sample["unit_title"]
        curr_t = sample["cluster_title"]
        q_texts = [r["question_text"] for r in recs[:3]]
        
        prompt = f"""
Course: {c_code}
Unit: {u_title} ({a_id})
Current Title: "{curr_t}"
Historical Examination Questions in this cluster:
{json.dumps(q_texts, indent=2)}

Task:
Formulate an authoritative, clean, academic title (4 to 8 words) for this examination cluster.
Strict Rules:
- No quotation marks.
- No question prefixes (e.g. do not say "Explain...", "Discuss...").
- No OCR fragments, ellipses (...), or raw tags.
- Capitalize properly like an academic chapter title.

Output strictly as JSON:
{{"refined_title": "..."}}
"""
        messages = [
            {"role": "system", "content": "You are an expert academic curriculum editor for IGNOU MA Public Administration. Output strict JSON only."},
            {"role": "user", "content": prompt}
        ]
        res, _ = groq_assistant.call_groq_api(messages, model=groq_assistant.PRIMARY_MODEL, temperature=0.1)
        ref_t = res.get("refined_title")
        if ref_t and len(ref_t) > 5 and not is_unclean_title(ref_t):
            updated_titles[cid] = ref_t
        else:
            # fallback clean
            clean_str = re.sub(r'^(Rti:|Marx:|Taylor:|Tqm:|Sala:|Bureaucracy:|Civil Society:|Describe the|Explain the|Analyse the)\s*', '', curr_t, flags=re.I).strip(" '\".,;:-")
            clean_str = re.sub(r'\.\.\..*', '', clean_str).strip()
            updated_titles[cid] = clean_str.title() if len(clean_str) > 5 else curr_t

    # Apply updates
    for r in records:
        cid = r["cluster_id"]
        if cid in updated_titles:
            r["cluster_title"] = updated_titles[cid]
            
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        w.writeheader()
        w.writerows(records)
        
    print(f"Applied title polish to {len(updated_titles)} clusters and saved {CSV_PATH}")

if __name__ == "__main__":
    clean_all_unclean_titles()
