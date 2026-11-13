import json
from pathlib import Path
import sys

ROOT = Path('D:/Stuff/ExamForge')
sys.path.append(str(ROOT / 'engine_v31_experiment/pyq_extraction'))
import groq_assistant
import ebook_extractor

OUTPUT_DIR = ROOT / 'engine_v31_experiment/pyq_extraction/outputs'
MODEL_ANSWERS_PATH = OUTPUT_DIR / 'model_answers.json'

d = json.load(open(MODEL_ANSWERS_PATH, encoding='utf-8'))
cid = 'MPA011-U21_C01'
print('Generating for:', cid)

u_title = 'Administrative Ethics'
c_title = 'Foundations and Concerns of Ethics in Public Administration'
fmt = 'SPLIT_10M'
marks = '10'
rep_q = 'What are the foci and concerns of administrative ethics? Discuss.'
target_words = 'approx. 220-250 words'

ebook_excerpt = ebook_extractor.extract_unit_text('MPA-011', [21], max_chars=2200)

prompt = f"""
You are a senior professor of Public Administration writing an official model examination answer for IGNOU MA Public Administration (MPA-011).
Course: MPA-011
Unit: {u_title} (MPA011-U21)
Cluster Theme: {c_title}
Question Format: {fmt} ({marks} Marks)
Target Length: {target_words}
Examination Question:
"{rep_q}"

OFFICIAL IGNOU EBOOK EXCERPT:
\"\"\"{ebook_excerpt[:2200]}\"\"\"

INSTRUCTIONS:
1. Write a comprehensive, high-scoring model answer directly addressing the question.
2. Ground all definitions, theories, thinkers, and statutory references PRIMARILY in the official IGNOU study materials.
3. Organize the answer into standard academic sections:
   - introduction: Clear conceptual foundation & definition
   - body_sections: List of 3 sections, each with a 'heading' and substantive 'content' paragraph
   - critical_evaluation: Academic critique, contemporary relevance, or limitations
   - conclusion: Synthesizing final perspective
   - key_thinkers_cited: List of specific theorists, thinkers, or statutory bodies cited

Return strictly valid JSON:
{{
    "question": "{rep_q}",
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
    {"role": "system", "content": "You are an expert academic evaluator for IGNOU Public Administration. Output a single strict JSON object only."},
    {"role": "user", "content": prompt}
]

res, is_cached = groq_assistant.call_groq_api(messages, model=groq_assistant.PRIMARY_MODEL, temperature=0.1)
if isinstance(res, list) and len(res) > 0 and isinstance(res[0], dict):
    res = res[0]

print("Got res type:", type(res))
if isinstance(res, dict) and res.get("introduction"):
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

    d[cid] = {
        "cluster_id": cid,
        "course_id": "MPA-011",
        "analytical_unit_id": "MPA011-U21",
        "unit_title": u_title,
        "cluster_title": c_title,
        "representative_question": rep_q,
        "format": fmt,
        "marks": marks,
        "word_count_target": target_words,
        "structured_data": res,
        "full_model_answer_html": full_html
    }

    MODEL_ANSWERS_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print("SUCCESS: Successfully saved MPA011-U21_C01!")
else:
    print("FAILED:", res)
