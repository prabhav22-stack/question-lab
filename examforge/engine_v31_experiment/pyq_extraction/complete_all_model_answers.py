import os
import sys
import csv
import json
import re
import time
from pathlib import Path

ROOT = Path("D:/Stuff/ExamForge")
sys.path.append(str(ROOT / "engine_v31_experiment/pyq_extraction"))
import ebook_extractor
import groq_assistant

OUTPUT_DIR = ROOT / "engine_v31_experiment/pyq_extraction/outputs"
CSV_PATH = OUTPUT_DIR / "locked_units_clustered_pyqs.csv"
MODEL_ANSWERS_PATH = OUTPUT_DIR / "model_answers.json"

def complete_all_48_model_answers():
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
            
    # Filter out entries with errors
    valid_count = 0
    for k, v in list(model_answers.items()):
        s = v.get("structured_data", {})
        if isinstance(s, dict) and s.get("introduction"):
            valid_count += 1
        else:
            del model_answers[k]
            
    print(f"Valid model answers currently in cache: {valid_count} / {len(r1_clusters)}")
    
    for idx, (cid, recs) in enumerate(r1_clusters.items(), 1):
        if cid in model_answers:
            print(f"[{idx}/{len(r1_clusters)}] Skipping already valid: {cid}")
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
            
        ebook_excerpt = ebook_extractor.extract_unit_text(c_code, u_nums, max_chars=2200)
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
\"\"\"{ebook_excerpt[:2200]}\"\"\"

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
        
        # Retry with exponential backoff on 429
        max_retries = 5
        res = None
        for attempt in range(max_retries):
            res, is_cached = groq_assistant.call_groq_api(messages, model=groq_assistant.PRIMARY_MODEL, temperature=0.1)
            if isinstance(res, dict) and res.get("status") == "FAILED" and "429" in str(res.get("error", "")):
                wait_sec = (attempt + 1) * 7
                print(f"Rate limited (429). Backing off for {wait_sec}s...")
                time.sleep(wait_sec)
            else:
                break
                
        if not isinstance(res, dict) or not res.get("introduction"):
            print(f"Warning: Failed to generate for {cid}: {res}")
            time.sleep(2)
            continue
            
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
        
        MODEL_ANSWERS_PATH.write_text(json.dumps(model_answers, indent=2), encoding="utf-8")
        time.sleep(2.0) # Respectful pacing to prevent 429 errors
        
    print(f"Generation finished! Total valid model answers: {len(model_answers)} / 48")

if __name__ == "__main__":
    complete_all_48_model_answers()
