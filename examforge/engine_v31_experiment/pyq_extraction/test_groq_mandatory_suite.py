import os
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Primary model: openai/gpt-oss-120b (supports structured outputs, json_mode, tools)
# Reviewer model: openai/gpt-oss-20b
PRIMARY_MODEL = os.environ.get("GROQ_MODEL_PRIMARY", "openai/gpt-oss-120b")
REVIEWER_MODEL = os.environ.get("GROQ_MODEL_REVIEWER", "openai/gpt-oss-20b")

def run_test(name, prompt, model=PRIMARY_MODEL, system_prompt="You are an expert academic assistant for IGNOU Public Administration. Output strict valid JSON only."):
    print(f"--- Running Test: {name} on {model} ---")
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.1
    }).encode("utf-8")
    
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "ExamForge-Groq-Verification"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            print(f"Result [{name}]: PASSED. Keys: {list(parsed.keys())}")
            return True, parsed
    except Exception as e:
        print(f"Result [{name}]: FAILED with error: {e}")
        return False, str(e)

def run_suite():
    results = {}
    
    # 1. Connectivity & Structured JSON test
    ok, res = run_test("1_connectivity_json", "Return JSON: {\"status\": \"CONNECTED\", \"model_tested\": \"gpt-oss-120b\"}")
    results["1_connectivity_json"] = ok
    
    # 2. Thinker alias recognition (Chester Barnard)
    t2_prompt = """
    Determine if 'Chester Bernard' and 'C.I. Barnard' refer to the same administrative theorist Chester Barnard.
    Return JSON: {"alias_match": true/false, "canonical_name": "...", "confidence": 0.0-1.0}
    """
    ok, res = run_test("2_thinker_alias", t2_prompt)
    results["2_thinker_alias"] = ok and res.get("alias_match") is True
    
    # 3. Obvious same-concept pair
    t3_prompt = """
    Compare Question A: 'Explain Taylor's Scientific Management and mental revolution.'
    and Question B: 'Critically examine the core principles of Scientific Management formulated by F.W. Taylor.'
    Return JSON: {
        "same_concept": true/false,
        "decision": "SAME_CONCEPT" / "DIFFERENT_CONCEPT",
        "shared_concept": "...",
        "confidence": 0.0-1.0
    }
    """
    ok, res = run_test("3_same_concept_pair", t3_prompt)
    results["3_same_concept_pair"] = ok and res.get("same_concept") is True
    
    # 4. Intentionally similar words but conceptually different pair
    t4_prompt = """
    Compare Question A: 'Examine Herbert Simon's Bounded Rationality model of decision making.'
    and Question B: 'Discuss Elton Mayo's Hawthorne studies on informal group dynamics.'
    Both mention human behaviour in administration. Are they the SAME concept or DIFFERENT concepts?
    Return JSON: {
        "same_concept": true/false,
        "decision": "SAME_CONCEPT" / "DIFFERENT_CONCEPT",
        "confidence": 0.0-1.0
    }
    """
    ok, res = run_test("4_different_concept_pair", t4_prompt)
    results["4_different_concept_pair"] = ok and res.get("same_concept") is False
    
    # 5. Canonical subtopic mapping without hallucinating IDs
    t5_prompt = """
    The question is: 'Discuss the concept of Swaraj and critique of modern western civilization.'
    Unit: MPA011-U06 Gandhian Perspective.
    Official Subtopics available:
    - MPA011-U06-T6_2: 'Gandhian Concept of Swaraj'
    - MPA011-U06-T6_3: 'Critique of Modern Industrial Society'
    - MPA011-U06-T6_4: 'Decentralisation and Trusteeship'
    Map this question to the single best subtopic ID strictly from the list above. Do NOT invent IDs.
    Return JSON: {
        "canonical_subtopic_id": "...",
        "official_subtopic_title": "...",
        "confidence": 0.0-1.0
    }
    """
    ok, res = run_test("5_subtopic_mapping", t5_prompt)
    results["5_subtopic_mapping"] = ok and res.get("canonical_subtopic_id") in ["MPA011-U06-T6_2", "MPA011-U06-T6_3"]
    
    # 6. Refusal to invent invalid subtopic ID
    t6_prompt = """
    The question tests Quantum Administration.
    The allowed subtopics for Unit MPA011-U06 are ONLY:
    - MPA011-U06-T6_2: 'Gandhian Concept of Swaraj'
    - MPA011-U06-T6_3: 'Critique of Modern Industrial Society'
    Can it be mapped to these, or is it UNMAPPED?
    Return JSON: {
        "match_type": "UNMAPPED" or "DIRECT",
        "canonical_subtopic_id": "NONE" or valid ID from list,
        "explanation": "..."
    }
    """
    ok, res = run_test("6_refusal_to_invent_id", t6_prompt)
    results["6_refusal_to_invent_id"] = ok and res.get("match_type") == "UNMAPPED"

    # 7. Reviewer model check on deliberately inserted error
    t7_prompt = """
    Inspect this student statement: 'F.W. Taylor proposed the Hierarchy of Needs theory in 1943.'
    Fact check: Did Taylor propose Hierarchy of Needs, or did Abraham Maslow?
    Return JSON: {
        "verdict": "REQUIRES_REVISION" or "PASS",
        "error_identified": true/false,
        "correct_theorist": "Abraham Maslow"
    }
    """
    ok, res = run_test("7_reviewer_error_detection", t7_prompt, model=REVIEWER_MODEL)
    results["7_reviewer_error_detection"] = ok and res.get("error_identified") is True

    print("\n===============================")
    print("MANDATORY GROQ TEST SUITE SUMMARY:")
    for k, v in results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")
    all_passed = all(results.values())
    print(f"Overall Result: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print("===============================\n")
    return all_passed

if __name__ == "__main__":
    run_suite()
