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

def refine_titles_and_subtopics():
    print("Step A: Loading clusters and official topic registry...")
    with open(CSV_PATH, encoding="utf-8") as f:
        records = list(csv.DictReader(f))
        
    topics = list(csv.DictReader(open(TOPIC_REGISTRY_PATH, encoding="utf-8")))
    
    # Map topics by (course_code, unit_number)
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
        
    print(f"Total clusters to process: {len(cluster_records)}")
    
    refined_clusters_map = {}
    provenance_entries = []
    
    for cid, recs in cluster_records.items():
        sample_q = recs[0]
        c_code = sample_q["course_id"]
        a_id = sample_q["analytical_unit_id"]
        u_title = sample_q["unit_title"]
        curr_title = sample_q["cluster_title"]
        
        # Get allowed syllabus topics
        # For combined unit MPA011-U01+U02, pull both 1 and 2
        cand_topics = []
        if a_id == "MPA011-U01+U02":
            cand_topics.extend(unit_topics.get((c_code, 1), []))
            cand_topics.extend(unit_topics.get((c_code, 2), []))
        else:
            # extract unit number from canonical_unit_id e.g. MPA012-U04 -> 4
            m = re.search(r'U(\d+)', sample_q["canonical_unit_id"])
            if m:
                u_n = int(m.group(1))
                cand_topics.extend(unit_topics.get((c_code, u_n), []))
                
        # Filter generic topics
        filtered_topics = [
            t for t in cand_topics 
            if not any(x in t["official_topic_title"].lower() for x in ["introduction", "conclusion", "learning outcome", "references", "activity"])
        ]
        
        # Question texts
        q_texts = [r["question_text"] for r in recs[:3]]
        
        prompt = f"""
        Course: {c_code}
        Unit: {u_title} ({a_id})
        Current Auto-Cluster Title: "{curr_title}"
        Representative Historical Questions:
        {json.dumps(q_texts, indent=2)}

        Official Syllabus Subtopics for this Unit:
        {json.dumps([f"{t['canonical_topic_id']}: {t['official_topic_title']}" for t in filtered_topics[:8]], indent=2)}

        Tasks:
        1. Formulate a crisp, academic cluster title (max 8-10 words) that accurately captures what this question theme tests.
        2. Identify the single best matching canonical syllabus topic strictly from the provided list (or UNMAPPED if none fit).
        3. Identify whether this tests a Specific Model/Theorist, Institutional Mechanism, or Conceptual Framework.

        Return strictly valid JSON:
        {{
            "refined_cluster_title": "...",
            "canonical_topic_id": "...",
            "matched_topic_title": "...",
            "analytical_category": "Theorist/Model" or "Institutional Framework" or "Concept/Process",
            "confidence": 0.0-1.0
        }}
        """
        messages = [
            {"role": "system", "content": "You are an expert academic curriculum auditor for IGNOU Public Administration. Output strict JSON only."},
            {"role": "user", "content": prompt}
        ]
        res, is_cached = groq_assistant.call_groq_api(messages, model=groq_assistant.PRIMARY_MODEL)
        
        ref_title = res.get("refined_cluster_title", curr_title).strip()
        matched_topic_id = res.get("canonical_topic_id", "UNMAPPED")
        matched_topic_title = res.get("matched_topic_title", "General Unit Theme")
        conf = float(res.get("confidence", 0.90))
        
        refined_clusters_map[cid] = {
            "refined_title": ref_title,
            "canonical_topic_id": matched_topic_id,
            "matched_topic_title": matched_topic_title,
            "confidence": conf
        }
        
        provenance_entries.append({
            "operation": "SEMANTIC_TITLE_AND_SUBTOPIC_MAPPING",
            "cluster_id": cid,
            "course_id": c_code,
            "old_title": curr_title,
            "refined_title": ref_title,
            "matched_topic_id": matched_topic_id,
            "confidence": conf
        })
        
    print("Refinement completed across all clusters.")
    
    # Update CSV records with refined title & subtopic mapping
    for r in records:
        cid = r["cluster_id"]
        if cid in refined_clusters_map:
            r["cluster_title"] = refined_clusters_map[cid]["refined_title"]
            r["canonical_subtopic_id"] = refined_clusters_map[cid]["canonical_topic_id"]
            r["official_subtopic_title"] = refined_clusters_map[cid]["matched_topic_title"]
            
    # Rewrite CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        fieldnames = list(records[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
        
    print(f"Updated CSV with refined titles and canonical mappings: {CSV_PATH}")
    
    # Save provenance log
    prov_file = OUTPUT_DIR / "groq_semantic_refinement_provenance.csv"
    with open(prov_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(provenance_entries[0].keys()))
        writer.writeheader()
        writer.writerows(provenance_entries)
    print(f"Saved refinement provenance log: {prov_file}")

if __name__ == "__main__":
    refine_titles_and_subtopics()
