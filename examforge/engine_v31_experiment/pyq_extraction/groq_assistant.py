import os
import sys
import json
import urllib.request
import urllib.error
import hashlib
from pathlib import Path

ROOT = Path("D:/Stuff/ExamForge")
CACHE_DIR = ROOT / "engine_v31_experiment/pyq_extraction/groq_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Load from .env if present
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.strip().split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
API_URL = "https://api.groq.com/openai/v1/chat/completions"

PRIMARY_MODEL = os.environ.get("GROQ_MODEL_PRIMARY", "openai/gpt-oss-120b")
REVIEWER_MODEL = os.environ.get("GROQ_MODEL_REVIEWER", "openai/gpt-oss-20b")

def get_cache_key(prefix, payload_dict):
    raw = json.dumps(payload_dict, sort_keys=True).encode("utf-8")
    return CACHE_DIR / f"{prefix}_{hashlib.sha256(raw).hexdigest()}.json"

def call_groq_api(messages, model=PRIMARY_MODEL, response_format={"type": "json_object"}, temperature=0.1):
    payload = {
        "model": model,
        "messages": messages,
        "response_format": response_format,
        "temperature": temperature
    }
    cache_file = get_cache_key(model.replace("/", "_"), payload)
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8")), True
        except:
            pass
            
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=req_data,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "ExamForge-Pipeline-v31"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            cache_file.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
            return parsed, False
    except Exception as e:
        return {"error": str(e), "status": "FAILED"}, False

def generate_answer_framework_with_ebook(cluster_title, sample_questions, course_code, unit_title, format_type, ebook_excerpt):
    """
    Generate an authentic answer preparation framework based primarily on the official IGNOU unit ebook excerpt.
    """
    prompt = f"""
    You are an authoritative professor of Public Administration writing an examination preparation framework for IGNOU MA Public Administration ({course_code}).
    Course: {course_code}
    Unit: {unit_title}
    Exam Theme / Cluster: {cluster_title}
    Question Format: {format_type} (20 Marks = ~500 words essay; 10 Marks = ~250 words short note)
    Representative Historical Questions:
    {json.dumps([q.get('question_text') for q in sample_questions[:3]], indent=2)}

    PRIMARY AUTHORITATIVE SOURCE EXCERPT FROM OFFICIAL IGNOU EBOOK:
    \"\"\"{ebook_excerpt[:3500]}\"\"\"

    Strict Instructions:
    1. Base all headings, conceptual foundations, thinkers, principles, and models PRIMARILY on the official IGNOU ebook excerpt provided above.
    2. Do NOT invent external thinkers or unverified theories not found in IGNOU study materials.
    3. Structure the output as an actionable, high-scoring examination framework:
       - suggested_introduction: Clear definitional foundation & context from IGNOU text.
       - core_dimensions: 4 to 6 substantive analytical points/headings reflecting the ebook structure.
       - key_thinkers_and_models: Specific theorists, concepts, or schemes cited in the unit.
       - critical_evaluation: Genuine academic appraisal / contemporary limitations as per IGNOU material.
       - suggested_conclusion: Crisp synthesizing summary.
       - essential_keywords: 6-8 core terms for memorisation.
    
    Output strictly as JSON:
    {{
        "theme": "{cluster_title}",
        "suggested_introduction": "...",
        "core_dimensions": ["...", "..."],
        "key_thinkers_and_models": ["...", "..."],
        "critical_evaluation": "...",
        "suggested_conclusion": "...",
        "essential_keywords": ["...", "..."]
    }}
    """
    messages = [
        {"role": "system", "content": "You are an expert academic assistant for IGNOU Public Administration. Output strict JSON only."},
        {"role": "user", "content": prompt}
    ]
    res, is_cached = call_groq_api(messages, model=PRIMARY_MODEL)
    return res

def review_answer_framework_with_ebook(framework, cluster_title, course_code, unit_title, ebook_excerpt):
    """
    Independent review of generated framework against the official IGNOU ebook excerpt using the reviewer model.
    """
    prompt = f"""
    Review this proposed IGNOU examination answer framework against the supplied official IGNOU ebook excerpt.
    Course: {course_code}
    Unit: {unit_title}
    Theme: {cluster_title}
    Proposed Framework:
    {json.dumps(framework, indent=2)}

    OFFICIAL IGNOU EBOOK EXCERPT:
    \"\"\"{ebook_excerpt[:2500]}\"\"\"

    Review Criteria:
    1. Factual fidelity: Are thinkers, principles, and concepts strictly aligned with the official IGNOU unit text?
    2. Freedom from hallucination: Are there any fabricated external theories or unsupported claims?
    3. Academic depth: Is it suitable for scoring high marks in IGNOU Term-End Examinations?

    Return strictly JSON:
    {{
        "verdict": "PASS" or "PASS_WITH_MINOR_WARNINGS" or "REQUIRES_REVISION",
        "factual_accuracy_score": 0.0-1.0,
        "comments": "...",
        "correction_needed": "None" or specific recommendation
    }}
    """
    messages = [
        {"role": "system", "content": "You are a senior academic auditor for IGNOU examinations. Output strict JSON only."},
        {"role": "user", "content": prompt}
    ]
    res, is_cached = call_groq_api(messages, model=REVIEWER_MODEL)
    return res
