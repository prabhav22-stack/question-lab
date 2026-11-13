"""NVIDIA NIM and OpenRouter AI integration service for Question Lab and ExamForge.

Provides high-speed inference via NVIDIA's NIM API (https://integrate.api.nvidia.com/v1)
and OpenRouter (https://openrouter.ai/api/v1) for conceptual doubt-solving, syllabus inquiries,
and essay evaluation.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

import config

NVIDIA_NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

NVIDIA_MODELS: Dict[str, str] = {
    "nvidia/nemotron-3.5-super-vl:free": "NVIDIA Nemotron 3.5 Super VL [Free via OpenRouter] (Recommended)",
    "nvidia/nemotron-3.5-lightning:free": "NVIDIA Nemotron 3.5 Lightning [Free via OpenRouter] (Fast Reasoning)",
    "nvidia/nemotron-3-ultra-550b-a55b:free": "NVIDIA Nemotron 3 Ultra 550B [Free via OpenRouter]",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free": "NVIDIA Nemotron 3 Nano Omni Reasoning [Free via OpenRouter]",
    "meta/llama-3.3-70b-instruct": "Llama 3.3 70B Instruct [NVIDIA NIM Direct]",
    "nvidia/llama-3.1-nemotron-70b-instruct": "NVIDIA Llama 3.1 Nemotron 70B [NVIDIA NIM Direct]",
    "deepseek-ai/deepseek-r1": "DeepSeek R1 [NVIDIA NIM Direct]",
    "mistralai/mixtral-8x22b-instruct": "Mixtral 8x22B Instruct [NVIDIA NIM Direct]",
    "meta/llama-3.1-8b-instruct": "Llama 3.1 8B Instruct [NVIDIA NIM Direct]",
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
    """Execute a query against NVIDIA NIM or OpenRouter API.

    Returns:
        (success: bool, response_or_error: str)
    """
    key = (api_key if api_key is not None else config.get_nvidia_api_key()).strip()
    if not key or key in ("YOUR_NVIDIA_API_KEY", "YOUR_OPENROUTER_API_KEY"):
        return (
            False,
            "NVIDIA / OpenRouter API Key not configured. Please enter your API key (starts with 'nvapi-' or 'sk-or-').",
        )

    target_model = model or config.get_nvidia_model() or DEFAULT_NVIDIA_MODEL

    # Determine endpoint based on API key prefix or model name
    is_openrouter = key.startswith("sk-or-") or ":free" in target_model or "openrouter" in target_model.lower()
    endpoint = OPENROUTER_API_URL if is_openrouter else NVIDIA_NIM_URL

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload: Dict[str, Any] = {
        "model": target_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if not is_openrouter:
        payload["top_p"] = 0.95

    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }
    if is_openrouter:
        headers["HTTP-Referer"] = "https://question-lab.streamlit.app"
        headers["X-Title"] = "Question Lab"
    else:
        headers["User-Agent"] = "QuestionLab-ExamForge/3.1"

    req = urllib.request.Request(
        endpoint,
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
                    # Handle reasoning models where main content or thought output is in reasoning
                    if not content:
                        content = msg_obj.get("reasoning")
                    if content:
                        return (True, str(content).strip())
                    return (False, "API returned an empty response content.")
                return (False, "API returned an empty choices list.")
            return (False, f"API error: HTTP status {status_code} - {raw_body}")
    except urllib.error.HTTPError as http_err:
        err_msg = http_err.read().decode("utf-8", errors="ignore")
        return (False, f"API HTTP {http_err.code}: {err_msg}")
    except urllib.error.URLError as url_err:
        return (False, f"Network connection error to API: {url_err.reason}")
    except Exception as exc:
        return (False, f"Unexpected error during API request: {exc}")


def ask_examforge_question(
    user_query: str,
    course_id: str,
    unit_id: str,
    unit_title: str,
    representative_pyq: str = "",
    model_answer_summary: str = "",
    model: str = DEFAULT_NVIDIA_MODEL,
    api_key: Optional[str] = None,
) -> Tuple[bool, str]:
    """Ask a question grounded in the ExamForge syllabus context using NVIDIA AI."""
    system_prompt = (
        "You are an expert Professor of Public Administration and veteran Civil Services Examination "
        "(UPSC & BPSC Optional) Evaluator. You provide intellectually rigorous, academically grounded, "
        "and well-structured responses citing authoritative administrative thinkers, theorists, "
        "and constitutional provisions where appropriate."
    )

    context_parts = [
        f"**Target Course:** {course_id}",
        f"**Syllabus Unit:** {unit_id} - {unit_title}",
    ]
    if representative_pyq:
        context_parts.append(f"**Representative Exam PYQ:** \"{representative_pyq}\"")
    if model_answer_summary:
        context_parts.append(f"**Core Theoretical Framework:** {model_answer_summary[:1200]}")

    full_prompt = (
        f"CONTEXT ON CURRENT SYLLABUS UNIT:\n"
        + "\n".join(context_parts)
        + "\n\n"
        + f"STUDENT QUESTION / DOUBT:\n"
        f"{user_query}\n\n"
        "INSTRUCTIONS:\n"
        "1. Provide a direct, well-structured, and comprehensive answer suitable for UPSC/BPSC/MPA level.\n"
        "2. Cite key thinkers, classical & modern administrative theorists (e.g., Woodrow Wilson, Taylor, Fayol, Weber, Mary Parker Follett, Herbert Simon, Dwight Waldo, Fred Riggs, Vincent Ostrom) where relevant.\n"
        "3. Provide contemporary Indian administrative examples or constitutional/statutory provisions where applicable.\n"
        "4. Conclude with a crisp, balanced analytical summary."
    )

    return query_nvidia_ai(
        prompt=full_prompt,
        system_prompt=system_prompt,
        model=model,
        api_key=api_key,
        temperature=0.3,
        max_tokens=2500,
    )
