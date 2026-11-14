"""OpenRouter NVIDIA AI integration service for Question Lab and ExamForge.

Provides high-speed inference via OpenRouter (https://openrouter.ai/api/v1)
for NVIDIA's premier reasoning and vision models (Nemotron 3.5 Super VL,
Nemotron 3.5 Lightning, Nemotron 3 Ultra 550B, and Nemotron 3 Nano Omni).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

import config

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

NVIDIA_MODELS: Dict[str, str] = {
    "nvidia/nemotron-3.5-super-vl:free": "NVIDIA Nemotron 3.5 Super VL (Free) [Recommended]",
    "nvidia/nemotron-3.5-lightning:free": "NVIDIA Nemotron 3.5 Lightning (Free) [Fast Reasoning]",
    "nvidia/nemotron-3-ultra-550b-a55b:free": "NVIDIA Nemotron 3 Ultra 550B (Free) [Deep Analysis]",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free": "NVIDIA Nemotron 3 Nano Omni Reasoning (Free)",
}

DEFAULT_NVIDIA_MODEL = "nvidia/nemotron-3.5-super-vl:free"


def query_nvidia_ai(
    prompt: str,
    system_prompt: str = "",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = 0.4,
    max_tokens: int = 2048,
    timeout: int = 45,
) -> Tuple[bool, str]:
    """Execute a query against OpenRouter for NVIDIA models.

    Returns:
        (success: bool, response_or_error: str)
    """
    key = (api_key if api_key is not None else config.get_nvidia_api_key()).strip()
    if not key or key in ("YOUR_NVIDIA_API_KEY", "YOUR_OPENROUTER_API_KEY"):
        return (
            False,
            "OpenRouter API Key not configured. Please enter your OpenRouter key (starts with 'sk-or-v1-').",
        )

    target_model = model or config.get_nvidia_model() or DEFAULT_NVIDIA_MODEL

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload: Dict[str, Any] = {
        "model": target_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 5000,
    }

    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "https://ps-question-lab.streamlit.app",
        "X-Title": "Question Lab",
    }

    req = urllib.request.Request(
        OPENROUTER_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status_code = response.getcode()
            raw_body = response.read().decode("utf-8")
            if status_code == 200:
                data = json.loads(raw_body)
                choices = data.get("choices", [])
                if choices:
                    msg_obj = choices[0].get("message", {})
                    content = msg_obj.get("content")
                    # Handle reasoning models where output is placed in reasoning
                    if not content:
                        content = msg_obj.get("reasoning")
                    if content:
                        return (True, str(content).strip())
                    return (False, "API returned an empty response content.")
                return (False, "API returned an empty choices list.")
            return (False, f"API error: HTTP status {status_code} - {raw_body}")
    except urllib.error.HTTPError as http_err:
        err_msg = http_err.read().decode("utf-8", errors="ignore")
        return (False, f"OpenRouter API HTTP {http_err.code}: {err_msg}")
    except urllib.error.URLError as url_err:
        return (False, f"Network connection error to OpenRouter API: {url_err.reason}")
    except Exception as exc:
        return (False, f"Unexpected error during API request: {exc}")


def ask_examforge_question(
    user_query: str,
    course_id: str,
    unit_id: str,
    unit_title: str,
    representative_pyq: str = "",
    model_answer_summary: str = "",
    ebook_excerpt: str = "",
    model: str = DEFAULT_NVIDIA_MODEL,
    api_key: Optional[str] = None,
) -> Tuple[bool, str]:
    """Ask a question strictly grounded in official IGNOU ebooks and ExamForge syllabus context using NVIDIA AI."""
    system_prompt = (
        "You are an authoritative Professor of Public Administration and veteran Civil Services Examination "
        "(UPSC & BPSC Optional / IGNOU MPA) Evaluator. You provide comprehensive, rigorous, and fully completed "
        "answers based strictly on the official IGNOU self-learning material and ebooks. Never cut your answers short; "
        "always finish all sections thoroughly through the conclusion."
    )

    context_parts = [
        f"**Target Course:** {course_id}",
        f"**Syllabus Unit:** {unit_id} - {unit_title}",
    ]
    if representative_pyq:
        context_parts.append(f"**Representative Exam PYQ:** \"{representative_pyq}\"")
    if model_answer_summary:
        context_parts.append(f"**Verified Model Answer Framework:** {model_answer_summary[:1200]}")
    if ebook_excerpt:
        context_parts.append(f"\n**OFFICIAL IGNOU EBOOK CONTENT & READINGS (STRICT PRIMARY SOURCE):**\n{ebook_excerpt[:6500]}")

    full_prompt = (
        f"CONTEXT AND OFFICIAL COURSE MATERIAL:\n"
        + "\n".join(context_parts)
        + "\n\n"
        + f"STUDENT QUESTION / DOUBT:\n"
        f"{user_query}\n\n"
        "STRICT INSTRUCTIONS:\n"
        "1. Base your explanations, concepts, thinkers, arguments, and headings PRIMARILY on the official IGNOU ebook excerpt provided above.\n"
        "2. Provide an exhaustive, complete examination-oriented note/essay without truncating any section. Ensure the conclusion is fully written out.\n"
        "3. Cite key administrative thinkers, theorists, and conceptual models exactly as highlighted in the official IGNOU syllabus.\n"
        "4. Provide contemporary Indian administrative illustrations, constitutional articles, and institutional examples where relevant.\n"
        "5. Conclude with a crisp, balanced analytical summary and practical revision tips."
    )

    return query_nvidia_ai(
        prompt=full_prompt,
        system_prompt=system_prompt,
        model=model,
        api_key=api_key,
        temperature=0.3,
        max_tokens=5000,
        timeout=60,
    )
