"""
Targeted expansion of 3 thin model answers.
Bypasses cache by using a unique session tag in the prompt.
"""
import os, sys, json, re, time, hashlib
from pathlib import Path

ROOT = Path("D:/Stuff/ExamForge")
sys.path.append(str(ROOT / "engine_v31_experiment/pyq_extraction"))
import groq_assistant
import ebook_extractor

MA_PATH = ROOT / "engine_v31_experiment/pyq_extraction/outputs/model_answers.json"
CACHE_DIR = ROOT / "engine_v31_experiment/pyq_extraction/groq_cache"

model_answers = json.loads(MA_PATH.read_text(encoding="utf-8"))

THIN_TARGETS = {
    "MPA011-U12_C01": {"unit_nums": [12], "course": "MPA-011"},
    "MPA011-U19_C01": {"unit_nums": [19], "course": "MPA-011"},
    "MPA014-U01_C01": {"unit_nums": [1],  "course": "MPA-014"},
}

print("=== Targeted thin-answer expansion (cache-bypass mode) ===\n")

for cid, meta in THIN_TARGETS.items():
    entry = model_answers[cid]
    sd = entry["structured_data"]
    old_text = (sd.get("introduction","") + " " +
                " ".join(b.get("content","") for b in sd.get("body_sections",[])) + " " +
                sd.get("critical_evaluation","") + " " +
                sd.get("conclusion",""))
    old_wc = len(old_text.split())
    print(f"[{cid}] Current word count: {old_wc}")

    u_nums = meta["unit_nums"]
    c_code = meta["course"]
    ebook_excerpt = ebook_extractor.extract_unit_text(c_code, u_nums, max_chars=3500)

    rep_q = entry["representative_question"]
    u_title = entry["unit_title"]
    c_title = entry["cluster_title"]
    fmt = entry["format"]
    marks = entry["marks"]

    clean_rep_q = rep_q.replace('"', "'").strip()

    # Provide existing content as context to expand
    existing_intro = sd.get("introduction","")[:400] if sd.get("introduction") else ""
    existing_body_titles = [b.get("heading","") for b in sd.get("body_sections",[])]

    system_msg = (
        "You are a senior IGNOU MPA examinations professor. "
        "Write a full-length model answer. Output ONLY valid JSON. "
        "MINIMUM 500 words total across all fields. Each body section MUST have at least 90 words. "
        "If you cannot fill 500 words from IGNOU material, supplement with general public administration theory."
    )

    user_msg = f"""Write a COMPLETE, FULL-LENGTH model answer for IGNOU MPA {c_code}.

UNIT: {u_title}
TOPIC: {c_title}
EXAM QUESTION: "{clean_rep_q}"
FORMAT: FULL_20M (20 marks, needs 500-600 words MINIMUM)

OFFICIAL IGNOU EBOOK MATERIAL:
{ebook_excerpt[:3500]}

REQUIREMENT: The JSON output MUST total at least 500 words when all text fields are combined.
Write 4 body sections with at least 90 words each. Write a 100-word introduction. Write 80-word critical evaluation. Write 70-word conclusion.

Return ONLY this JSON (no other text):
{{
  "question": "{clean_rep_q}",
  "format_and_marks": "FULL_20M | 20 Marks",
  "target_word_count": "500-580 words",
  "introduction": "<write 100+ words here>",
  "body_sections": [
    {{"heading": "1. <heading>", "content": "<write 90+ words here>"}},
    {{"heading": "2. <heading>", "content": "<write 90+ words here>"}},
    {{"heading": "3. <heading>", "content": "<write 90+ words here>"}},
    {{"heading": "4. <heading>", "content": "<write 90+ words here>"}}
  ],
  "critical_evaluation": "<write 80+ words here>",
  "conclusion": "<write 70+ words here>",
  "key_thinkers_cited": ["thinker1", "thinker2", "thinker3"]
}}"""

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ]

    # Build cache key and DELETE it if it exists (force fresh generation)
    payload = {
        "model": groq_assistant.PRIMARY_MODEL,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0.2
    }
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    cache_file = CACHE_DIR / f"{groq_assistant.PRIMARY_MODEL.replace('/', '_')}_{hashlib.sha256(raw).hexdigest()}.json"
    if cache_file.exists():
        cache_file.unlink()
        print(f"  Cleared stale cache for {cid}")

    max_retries = 5
    res = None
    for attempt in range(max_retries):
        import urllib.request, urllib.error
        import urllib.request

        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            groq_assistant.API_URL,
            data=req_data,
            headers={
                "Authorization": f"Bearer {groq_assistant.GROQ_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "ExamForge-Pipeline-v31-Expand"
            }
        )
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                content = data["choices"][0]["message"]["content"]
                res = json.loads(content)
                cache_file.write_text(json.dumps(res, indent=2), encoding="utf-8")
                break
        except urllib.error.HTTPError as e:
            err_body = e.read().decode() if hasattr(e, 'read') else str(e)
            print(f"  Attempt {attempt+1} failed: {e.code} {err_body[:200]}")
            if "429" in str(e.code):
                wait = (attempt + 1) * 10
                print(f"  Rate limit. Waiting {wait}s...")
                time.sleep(wait)
            else:
                # For 400 errors, the prompt may be too long — try with shorter ebook excerpt
                print(f"  HTTP {e.code} error. Shortening ebook excerpt and retrying...")
                ebook_excerpt = ebook_excerpt[:1800]
                user_msg = user_msg.replace(ebook_excerpt[:3500], ebook_excerpt[:1800])
                # rebuild payload
                messages[1]["content"] = user_msg
                payload["messages"] = messages
                req_data = json.dumps(payload).encode("utf-8")
                time.sleep(3)
        except Exception as e:
            print(f"  Unexpected error: {e}")
            time.sleep(5)

    if not res or not isinstance(res, dict) or not res.get("introduction"):
        print(f"  FAILED for {cid}. Skipping.")
        continue

    # Verify word count
    new_text = (res.get("introduction","") + " " +
                " ".join(b.get("content","") for b in res.get("body_sections",[])) + " " +
                res.get("critical_evaluation","") + " " +
                res.get("conclusion",""))
    new_wc = len(new_text.split())
    print(f"  New word count: {new_wc} words", "✓" if new_wc >= 450 else "!! STILL THIN")

    if new_wc < 350:
        print(f"  REJECTED: too thin ({new_wc}w). Keeping original.")
        continue

    # Update model_answers
    model_answers[cid]["structured_data"] = res

    # Rebuild HTML
    intro = res.get("introduction", "")
    body_parts = []
    for sec in res.get("body_sections", []):
        h = sec.get("heading", "")
        c_text = sec.get("content", "")
        body_parts.append(f"<b>{h}</b><br/>{c_text}")
    body_full = "<br/><br/>".join(body_parts)
    eval_txt = res.get("critical_evaluation", "")
    concl = res.get("conclusion", "")
    full_html = (f"<b>Introduction:</b><br/>{intro}<br/><br/>"
                 f"{body_full}<br/><br/>"
                 f"<b>Critical Evaluation & Administrative Relevance:</b><br/>{eval_txt}<br/><br/>"
                 f"<b>Conclusion:</b><br/>{concl}")
    model_answers[cid]["full_model_answer_html"] = full_html

    MA_PATH.write_text(json.dumps(model_answers, indent=2), encoding="utf-8")
    print(f"  Saved {cid}. ✓")
    time.sleep(3)

# Final check
print("\n=== Final word count verification ===")
ma_check = json.loads(MA_PATH.read_text(encoding="utf-8"))
for cid in THIN_TARGETS:
    sd = ma_check[cid]["structured_data"]
    text = (sd.get("introduction","") + " " +
            " ".join(b.get("content","") for b in sd.get("body_sections",[])) + " " +
            sd.get("critical_evaluation","") + " " +
            sd.get("conclusion",""))
    wc = len(text.split())
    thinkers = sd.get("key_thinkers_cited", [])
    status = "✓ OK" if wc >= 450 else "!! THIN"
    print(f"  {cid}: {wc} words | thinkers={thinkers} | {status}")

print("\nDone!")
