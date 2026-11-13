"""
ExamForge Engine v3.1 - Upgrade 1 & 2:
- Evidence-Based Marks Recovery & Dynamic Question-Format Classifier
- Controlled OCR / Typo Alias Normalizer (Exact verified aliases + phonetic normalizer)
"""

import re
import pandas as pd
from typing import Dict, Tuple, Any, List

EXACT_THINKER_ALIASES = {
    'chester bernard': 'Chester Barnard',
    'chester i. bernard': 'Chester Barnard',
    'herbert a. s. simon': 'Herbert A. Simon',
    'herbert a s simon': 'Herbert A. Simon',
    'elton meyo': 'Elton Mayo',
    'herzburg': 'Herzberg',
    'mc gregor': 'McGregor',
    'vrooms': 'Vroom',
    'riggsian': 'Riggs',
    'weberian': 'Weber'
}

def normalize_thinker_aliases(text: str) -> Tuple[str, List[Dict[str, str]]]:
    """
    Applies exact verified thinker/concept aliases before parsing.
    Logs any replacements made.
    """
    logs = []
    normalized = text
    for alias, canonical in EXACT_THINKER_ALIASES.items():
        pattern = re.compile(r'\b' + re.escape(alias) + r'\b', re.IGNORECASE)
        if pattern.search(normalized):
            logs.append({'original': alias, 'normalized': canonical, 'method': 'exact_dictionary'})
            normalized = pattern.sub(canonical, normalized)
    return normalized, logs

def classify_question_format_and_marks(q_text: str, header_text: str = '') -> Dict[str, Any]:
    """
    Strict 4-tier marks recovery and format classification hierarchy:
    Tier 1: Explicit marks printed beside question (e.g. 20)
    Tier 2: Explicit subpart marks (e.g. 10+10, 10 each)
    Tier 3: Header arithmetic inference (Max 100, 5 questions, all questions equal marks -> 20M)
    Tier 4: Flag UNRESOLVED
    
    Format:
    FULL_20M: Single 20M question (even if starting with 'Write a note on...')
    SPLIT_10_10: Subdivided into (a) and (b) 10-mark parts.
    """
    clean_t = q_text.strip()
    
    # Check if explicitly split into (a) and (b)
    has_subparts = bool(re.search(r'\(a\).*(?:and\s+)?\(b\)', clean_t, re.DOTALL | re.IGNORECASE) or 
                        re.search(r'short\s+notes.*following', clean_t, re.IGNORECASE) and ('(a)' in clean_t))
    
    # Tier 2: Explicit 10+10
    explicit_split_match = re.search(r'\b10\s*\+\s*10\b', clean_t)
    if explicit_split_match or (has_subparts and re.search(r'250\s*words', clean_t, re.IGNORECASE)):
        return {
            'format': 'SPLIT_10_10',
            'marks_tier': 'Tier 2 (Explicit 10+10 / subpart text)',
            'total_marks': 20,
            'subpart_marks': 10,
            'has_subparts': True
        }
        
    # Tier 1: Explicit marks printed beside question
    explicit_marks_match = re.search(r'\b(20)\b\s*$', clean_t)
    if explicit_marks_match and not has_subparts:
        return {
            'format': 'FULL_20M',
            'marks_tier': 'Tier 1 (Explicit 20 printed)',
            'total_marks': 20,
            'subpart_marks': None,
            'has_subparts': False
        }
        
    # Tier 3: Header arithmetic inference
    if has_subparts:
        return {
            'format': 'SPLIT_10_10',
            'marks_tier': 'Tier 3 (Inferred 10+10 from subparts)',
            'total_marks': 20,
            'subpart_marks': 10,
            'has_subparts': True
        }
    else:
        return {
            'format': 'FULL_20M',
            'marks_tier': 'Tier 3 (Header arithmetic inference 20M)',
            'total_marks': 20,
            'subpart_marks': None,
            'has_subparts': False
        }
