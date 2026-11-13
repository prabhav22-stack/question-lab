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

def generate_robust_model_answers():
    print("Loading CSV records to identify Rank 1 clusters...")
    with open(CSV_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        
    r1_clusters = {}
    for r in rows:
        if int(r["cluster_rank"]) == 1:
            cid = r["cluster_id"]
            if cid not in r1_clusters:
                r1_clusters[cid] = []
            r1_clusters[cid].append(r)
            
    print(f"Total Rank 1 clusters: {len(r1_clusters)}")
    
    model_answers = {}
    if MODEL_ANSWERS_PATH.exists():
        try:
            model_answers = json.load(open(MODEL_ANSWERS_PATH, encoding="utf-8"))
        except:
            pass
            
    for idx, (cid, recs) in enumerate(r1_clusters.items(), 1):
        # Check if already successfully generated
        if cid in model_answers:
            s_data = model_answers[cid].get("structured_data", {})
            if "introduction" in s_data and s_data.get("introduction"):
                print(f"[{idx}/{len(r1_clusters)}] Already generated: {cid}")
                continue
                
        sample = recs[0]
        c_code = sample["course_id"]
        a_id = sample["analytical_unit_id"]
        u_title = sample["unit_title"]
        c_title = sample["cluster_title"]
        fmt = sample["format_type"]
        marks = sample["marks"]
        rep_q = sample["question_text"]
        
        target_words = "approx. 450-500 words" if fmt == "FULL_20M" else "approx. 220-250 words"
        
        if a_id == "MPA011-U01+U02":
            u_nums = [1, 2]
        else:
            m = re.search(r'U(\d+)', sample["canonical_unit_id"])
            u_nums = [int(m.group(1))] if m else [1]
            
        ebook_excerpt = ebook_extractor.extract_unit_text(c_code, u_nums, max_chars=2500)
        
        # Clean rep_q to avoid breaking JSON
        clean_rep_q = rep_q.replace('"', "'").strip()
        
        print(f"[{idx}/{len(r1_clusters)}] Generating Model Answer for {c_code} {a_id}: '{c_title[:30]}'...")
        
        prompt = f"""
You are a senior professor of Public Administration writing an official model examination answer for IGNOU MA Public Administration ({c_code}).
Course: {c_code}
Unit: {u_title} ({a_id})
Cluster Theme: {c_title}
Question Format: {fmt} ({marks} Marks)
Target Length: {target_words}
Examination Question:
"{clean_rep_q}"

OFFICIAL IGNOU EBOOK EXCERPT:
\"\"\"{ebook_excerpt[:2500]}\"\"\"

INSTRUCTIONS:
1. Write a comprehensive, high-scoring model answer directly addressing the question.
2. Ground all definitions, theories, thinkers, and statutory references PRIMARILY in the official IGNOU study materials.
3. Organize the answer into standard academic sections:
   - introduction: Clear conceptual foundation & definition
   - body_sections: List of 3 to 4 sections, each with a 'heading' and substantive 'content' paragraph
   - critical_evaluation: Academic critique, contemporary relevance, or limitations
   - conclusion: Synthesizing final perspective
   - key_thinkers_cited: List of specific theorists, thinkers, or statutory bodies cited

Return strictly valid JSON:
{{
    "question": "{clean_rep_q}",
    "format_and_marks": "{fmt} | {marks} Marks",
    "target_word_count": "{target_words}",
    "introduction": "...",
    "body_sections": [
        {{"heading": "Heading 1", "content": "Detailed academic paragraph..."}},
        {{"heading": "Heading 2", "content": "Detailed academic paragraph..."}},
        {{"heading": "Heading 3", "content": "Detailed academic paragraph..."}}
    ],
    "critical_evaluation": "...",
    "conclusion": "...",
    "key_thinkers_cited": ["Theorist 1", "Theorist 2"]
}}
"""
        messages = [
            {"role": "system", "content": "You are an expert academic evaluator for IGNOU Public Administration. Output strict JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        res, is_cached = groq_assistant.call_groq_api(messages, model=groq_assistant.PRIMARY_MODEL, temperature=0.1)
        
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
        
        # Save every 2 answers
        if idx % 2 == 0 or idx == len(r1_clusters):
            MODEL_ANSWERS_PATH.write_text(json.dumps(model_answers, indent=2), encoding="utf-8")
            
    print(f"All {len(model_answers)} model answers generated successfully at: {MODEL_ANSWERS_PATH}")

if __name__ == "__main__":
    generate_robust_model_answers()
