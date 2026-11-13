import os
import sys
import csv
import json
import re
from pathlib import Path

ROOT = Path("D:/Stuff/ExamForge")
sys.path.append(str(ROOT / "engine_v31_experiment/pyq_extraction"))
import ebook_extractor
import groq_assistant

OUTPUT_DIR = ROOT / "engine_v31_experiment/pyq_extraction/outputs"
CSV_PATH = OUTPUT_DIR / "locked_units_clustered_pyqs.csv"
MODEL_ANSWERS_PATH = OUTPUT_DIR / "model_answers.json"

def generate_all_model_answers():
    print("Loading CSV records to identify Rank 1 clusters for all 48 analytical units...")
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        
    # Group Rank 1 clusters
    r1_clusters = {}
    for r in rows:
        if int(r["cluster_rank"]) == 1:
            cid = r["cluster_id"]
            if cid not in r1_clusters:
                r1_clusters[cid] = []
            r1_clusters[cid].append(r)
            
    print(f"Total Rank 1 clusters to generate model answers for: {len(r1_clusters)}")
    
    # Load existing model answers if any
    model_answers = {}
    if MODEL_ANSWERS_PATH.exists():
        try:
            model_answers = json.load(open(MODEL_ANSWERS_PATH, encoding="utf-8"))
        except:
            pass
            
    prov_rows = []
    
    for idx, (cid, recs) in enumerate(r1_clusters.items(), 1):
        if cid in model_answers and "full_model_answer" in model_answers[cid]:
            print(f"[{idx}/{len(r1_clusters)}] Already generated for {cid}")
            continue
            
        sample = recs[0]
        c_code = sample["course_id"]
        a_id = sample["analytical_unit_id"]
        u_title = sample["unit_title"]
        c_title = sample["cluster_title"]
        fmt = sample["format_type"]
        marks = sample["marks"]
        rep_q = sample["question_text"]
        
        # Target word count based on format
        target_words = "approx. 450-500 words" if fmt == "FULL_20M" else "approx. 220-250 words"
        
        # Determine unit numbers for ebook extraction
        if a_id == "MPA011-U01+U02":
            u_nums = [1, 2]
        else:
            m = re.search(r'U(\d+)', sample["canonical_unit_id"])
            u_nums = [int(m.group(1))] if m else [1]
            
        ebook_excerpt = ebook_extractor.extract_unit_text(c_code, u_nums, max_chars=4000)
        
        print(f"[{idx}/{len(r1_clusters)}] Generating Model Answer for {c_code} {a_id}: '{c_title}' ({fmt})...")
        
        prompt = f"""
You are an authoritative professor of Public Administration writing an exemplary, full-length model examination answer for IGNOU MA Public Administration ({c_code}).
Course: {c_code}
Unit: {u_title} ({a_id})
Cluster Theme: {c_title}
Format: {fmt} ({marks} Marks)
Target Length: {target_words}
Representative Examination Question:
"{rep_q}"

OFFICIAL IGNOU EBOOK EXCERPT:
\"\"\"{ebook_excerpt[:3500]}\"\"\"

INSTRUCTIONS:
1. Write a complete, comprehensive, publication-grade model essay answer directly addressing the question.
2. Ground all definitions, administrative theories, thinker references, and structural arguments PRIMARILY in the official IGNOU study materials.
3. Organize the answer into standard academic sections:
   - Introduction (Conceptual foundation & definition)
   - Core Theoretical Framework & Thinkers
   - Substantive Analytical Dimensions (Use clear subheadings)
   - Critical Evaluation & Contemporary Administrative Relevance
   - Conclusion (Synthesizing perspective)
4. Do NOT use bullet fragments or short summaries; write continuous, polished academic paragraphs with appropriate headings.

Return strictly valid JSON:
{{
    "question": "{rep_q}",
    "format_and_marks": "{fmt} | {marks} Marks",
    "target_word_count": "{target_words}",
    "introduction": "...",
    "body_sections": [
        {{"heading": "...", "content": "..."}},
        {{"heading": "...", "content": "..."}},
        {{"heading": "...", "content": "..."}}
    ],
    "critical_evaluation": "...",
    "conclusion": "...",
    "key_thinkers_cited": ["...", "..."],
    "total_word_count": 480
}}
"""
        messages = [
            {"role": "system", "content": "You are a senior academic professor writing official model answers for IGNOU. Output strict JSON only."},
            {"role": "user", "content": prompt}
        ]
        res, is_cached = groq_assistant.call_groq_api(messages, model=groq_assistant.PRIMARY_MODEL, temperature=0.1)
        
        # Assemble full text
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
        
        model_answers[cid] = {
            "cluster_id": cid,
            "course_id": c_code,
            "analytical_unit_id": a_id,
            "unit_title": u_title,
            "cluster_title": c_title,
            "representative_question": rep_q,
            "format": fmt,
            "marks": marks,
            "word_count_target": target_words,
            "structured_data": res,
            "full_model_answer_html": full_html
        }
        
        prov_rows.append({
            "cluster_id": cid,
            "course_id": c_code,
            "unit_id": a_id,
            "question": rep_q[:60],
            "model": groq_assistant.PRIMARY_MODEL,
            "cached": is_cached
        })
        
        # Incremental save every 4 answers
        if idx % 4 == 0 or idx == len(r1_clusters):
            MODEL_ANSWERS_PATH.write_text(json.dumps(model_answers, indent=2), encoding="utf-8")
            print(f"Saved checkpoint with {len(model_answers)} model answers.")
            
    print(f"All {len(model_answers)} model answers generated and saved at: {MODEL_ANSWERS_PATH}")

if __name__ == "__main__":
    generate_all_model_answers()
