"""
Generate model answers for all Rank 2 Core unit clusters.
35 clusters × ~2.5s each ≈ ~90-120s total + rate-limit backoffs.
Saves into model_answers.json under key = cluster_id (same schema as Rank 1).
"""
import os, sys, json, re, time, csv
from pathlib import Path

ROOT = Path("D:/Stuff/ExamForge")
sys.path.append(str(ROOT / "engine_v31_experiment/pyq_extraction"))
import groq_assistant
import ebook_extractor

MA_PATH = ROOT / "engine_v31_experiment/pyq_extraction/outputs/model_answers.json"
CSV_PATH = ROOT / "engine_v31_experiment/pyq_extraction/outputs/locked_units_clustered_pyqs.csv"

# Load existing model answers (we append to this dict)
model_answers = json.loads(MA_PATH.read_text(encoding="utf-8"))
print(f"Existing model answers: {len(model_answers)}")

# Load CSV and get Rank 2 Core clusters
rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
rank2_clusters = {}
for r in rows:
    if int(r["cluster_rank"]) == 2 and r["portfolio_tier"] == "10_CORE":
        cid = r["cluster_id"]
        if cid not in rank2_clusters:
            rank2_clusters[cid] = []
        rank2_clusters[cid].append(r)

print(f"Rank 2 Core clusters to generate: {len(rank2_clusters)}")

# Skip already generated
to_generate = {k: v for k, v in rank2_clusters.items() if k not in model_answers}
print(f"Already cached: {len(rank2_clusters) - len(to_generate)}")
print(f"Need to generate: {len(to_generate)}")
print()

for idx, (cid, recs) in enumerate(to_generate.items(), 1):
    sample = recs[0]
    c_code = sample["course_id"]
    a_id = sample["analytical_unit_id"]
    u_title = sample["unit_title"]
    c_title = sample["cluster_title"]
    fmt = sample["format_type"]
    marks = sample["marks"]
    rep_q = sample["question_text"]

    # Get unit number for ebook
    if a_id == "MPA011-U01+U02":
        u_nums = [1, 2]
    else:
        m = re.search(r'U(\d+)', sample["canonical_unit_id"])
        u_nums = [int(m.group(1))] if m else [1]

    ebook_excerpt = ebook_extractor.extract_unit_text(c_code, u_nums, max_chars=2500)
    target_words = "approx. 500-550 words" if fmt == "FULL_20M" else "approx. 220-260 words"
    clean_rep_q = rep_q.replace('"', "'").strip()

    print(f"[{idx}/{len(to_generate)}] {c_code} {cid} | {fmt}/{marks}M | '{c_title[:40]}'...")

    prompt = f"""You are a senior professor of Public Administration writing an official model examination answer for IGNOU MA Public Administration ({c_code}).
Course: {c_code}
Unit: {u_title} ({a_id})
Cluster Theme: {c_title}
Question Format: {fmt} ({marks} Marks)
Target Length: {target_words}
Examination Question: "{clean_rep_q}"

OFFICIAL IGNOU EBOOK EXCERPT:
\"\"\"{ebook_excerpt[:2500]}\"\"\"

INSTRUCTIONS:
1. Write a comprehensive, high-scoring model answer directly addressing the question.
2. Ground all definitions, theories, thinkers, and statutory references PRIMARILY in the official IGNOU study materials.
3. Organize the answer into standard academic sections:
   - introduction: Clear conceptual foundation & definition
   - body_sections: List of 3 to 4 sections, each with a 'heading' and substantive 'content' paragraph (min 70 words each)
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
}}"""

    messages = [
        {"role": "system", "content": "You are an expert academic evaluator for IGNOU Public Administration. Output strict JSON only."},
        {"role": "user", "content": prompt}
    ]

    max_retries = 5
    res = None
    for attempt in range(max_retries):
        res, is_cached = groq_assistant.call_groq_api(messages, model=groq_assistant.PRIMARY_MODEL, temperature=0.1)
        if isinstance(res, dict) and res.get("status") == "FAILED" and "429" in str(res.get("error", "")):
            wait = (attempt + 1) * 8
            print(f"  Rate limited. Backing off {wait}s...")
            time.sleep(wait)
        else:
            break

    if not isinstance(res, dict) or not res.get("introduction"):
        print(f"  WARNING: Failed for {cid}: {res}")
        time.sleep(3)
        continue

    # Compute word count
    text = (res.get("introduction","") + " " +
            " ".join(b.get("content","") for b in res.get("body_sections",[])) + " " +
            res.get("critical_evaluation","") + " " +
            res.get("conclusion",""))
    wc = len(text.split())
    print(f"  Generated: {wc} words ✓")

    # Build HTML
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
        "cluster_rank": 2,
        "structured_data": res,
        "full_model_answer_html": full_html
    }

    MA_PATH.write_text(json.dumps(model_answers, indent=2), encoding="utf-8")
    time.sleep(2.5)

print(f"\nDone! Total model answers now: {len(model_answers)} (was 48)")
