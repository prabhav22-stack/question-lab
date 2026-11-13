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

def run_targeted_refinement():
    print("Loading CSV records and topic registry...")
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
        
    # Group unique clusters
    cluster_records = {}
    for r in records:
        cid = r["cluster_id"]
        if cid not in cluster_records:
            cluster_records[cid] = []
        cluster_records[cid].append(r)
        
    print(f"Total unique clusters to refine: {len(cluster_records)}")
    
    refined_map = {}
    prov_rows = []
    
    for cid, recs in cluster_records.items():
        sample = recs[0]
        c_code = sample["course_id"]
        a_id = sample["analytical_unit_id"]
        u_title = sample["unit_title"]
        raw_title = sample["cluster_title"]
        
        cand_topics = []
        if a_id == "MPA011-U01+U02":
            cand_topics.extend(unit_topics.get((c_code, 1), []))
            cand_topics.extend(unit_topics.get((c_code, 2), []))
        else:
            m = re.search(r'U(\d+)', sample["canonical_unit_id"])
            if m:
                u_n = int(m.group(1))
                cand_topics.extend(unit_topics.get((c_code, u_n), []))
                
        filtered_topics = [
            t for t in cand_topics 
            if not any(x in t["official_topic_title"].lower() for x in ["introduction", "conclusion", "learning outcome", "references", "activity"])
        ]
        
        q_texts = [r["question_text"] for r in recs[:3]]
        
        user_prompt = f"""
Course: {c_code}
Unit: {u_title} ({a_id})
Raw Extracted Question Samples:
{json.dumps(q_texts, indent=2)}

Available Official Syllabus Topics:
{json.dumps([f"{t['canonical_topic_id']}: {t['official_topic_title']}" for t in filtered_topics[:8]], indent=2)}

Instructions:
1. Provide a professional, academic title (5 to 8 words) for this examination cluster. Avoid truncated words, trailing dots, or raw OCR artefacts.
2. Select the most relevant official canonical topic ID from the list above. If none clearly match, return 'UNMAPPED'.
3. Classify into: 'Theorist/Model', 'Institutional Structure', 'Policy/Reform', or 'Concept/Theory'.

Return strictly valid JSON:
{{
    "refined_title": "...",
    "canonical_topic_id": "...",
    "official_topic_title": "...",
    "category": "...",
    "confidence": 0.95
}}
"""
        messages = [
            {"role": "system", "content": "You are a senior curriculum auditor for IGNOU Public Administration. Output strict JSON only."},
            {"role": "user", "content": user_prompt}
        ]
        res, is_cached = groq_assistant.call_groq_api(messages, model=groq_assistant.PRIMARY_MODEL, temperature=0.1)
        
        ref_title = res.get("refined_title")
        if not ref_title or len(ref_title) < 5:
            ref_title = raw_title
        top_id = res.get("canonical_topic_id", "UNMAPPED")
        top_title = res.get("official_topic_title", "General Unit Theme")
        conf = float(res.get("confidence", 0.92))
        
        refined_map[cid] = {
            "title": ref_title,
            "topic_id": top_id,
            "topic_title": top_title,
            "confidence": conf
        }
        prov_rows.append({
            "cluster_id": cid,
            "course_id": c_code,
            "old_title": raw_title,
            "refined_title": ref_title,
            "canonical_topic_id": top_id,
            "confidence": conf,
            "cached": is_cached
        })

    # Update records
    for r in records:
        cid = r["cluster_id"]
        if cid in refined_map:
            r["cluster_title"] = refined_map[cid]["title"]
            r["canonical_subtopic_id"] = refined_map[cid]["topic_id"]
            r["official_subtopic_title"] = refined_map[cid]["topic_title"]
            
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        w.writeheader()
        w.writerows(records)
        
    print(f"Successfully updated CSV with high-fidelity titles: {CSV_PATH}")
    
    prov_file = OUTPUT_DIR / "groq_targeted_refinement_provenance.csv"
    with open(prov_file, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(prov_rows[0].keys()))
        w.writeheader()
        w.writerows(prov_rows)
    print(f"Saved refinement provenance log: {prov_file}")

if __name__ == "__main__":
    run_targeted_refinement()
