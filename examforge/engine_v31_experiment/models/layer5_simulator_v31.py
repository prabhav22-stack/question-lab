"""
ExamForge Engine v3.1 - Layer 5:
Realistic Statutory Exam-Hall Simulator & Scoring Logic
- Full-depth Core Unit on FULL_20M slot = 20 marks
- Full-depth Core Unit on SPLIT_10_10 slot = 10 marks if 1 subpart covered, 20 marks if both covered
- Buffer Subtopic Skeleton (250 words) = 10 marks cap on short-note subpart, 10 marks partial salvage on 20M full question
- Strict Question Slot-Consumption: Only 5 questions attempted in total (at least 2 from Sec I, at least 2 from Sec II)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Set, Tuple, Any

def score_paper_realistic(core_units: Set[int], 
                          buffer_s1: int, 
                          buffer_s2: int, 
                          paper_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates realistic statutory score on a single paper:
    paper_questions: list of question dicts with:
      'question_number', 'section' ('Section I' or 'Section II'), 
      'format' ('FULL_20M' or 'SPLIT_10_10'),
      'units': list of units involved in question (len 1 for FULL_20M, len 2 for SPLIT_10_10)
    """
    buffer_set = {u for u in [buffer_s1, buffer_s2] if u is not None}
    
    # Calculate score attainable for each of the 10 questions
    q_candidates_s1 = []
    q_candidates_s2 = []
    
    for q in paper_questions:
        q_num = q['question_number']
        sec = q['section']
        fmt = q['format']
        u_list = q['units']
        
        q_score = 0
        if fmt == 'FULL_20M':
            u = u_list[0] if len(u_list) > 0 else -1
            if u in core_units:
                q_score = 20
            elif u in buffer_set:
                q_score = 10 # 10M partial salvage for buffer skeleton
        elif fmt == 'SPLIT_10_10':
            # Subparts (a) and (b)
            # 10M if in core, 10M if in buffer
            part_a = u_list[0] if len(u_list) > 0 else -1
            part_b = u_list[1] if len(u_list) > 1 else -1
            
            score_a = 10 if (part_a in core_units or part_a in buffer_set) else 0
            score_b = 10 if (part_b in core_units or part_b in buffer_set) else 0
            q_score = score_a + score_b
            
        if sec == 'Section I':
            q_candidates_s1.append((q_num, q_score))
        else:
            q_candidates_s2.append((q_num, q_score))
            
    # Statutory Rule: Pick 5 questions in total, at least 2 from Sec I, at least 2 from Sec II
    # That means either (3 from Sec I, 2 from Sec II) OR (2 from Sec I, 3 from Sec II)
    best_score = 0
    best_combo = None
    
    # Sort descending
    q_candidates_s1.sort(key=lambda x: x[1], reverse=True)
    q_candidates_s2.sort(key=lambda x: x[1], reverse=True)
    
    # Case 1: 3 from Sec I, 2 from Sec II
    if len(q_candidates_s1) >= 3 and len(q_candidates_s2) >= 2:
        score_3_2 = sum(x[1] for x in q_candidates_s1[:3]) + sum(x[1] for x in q_candidates_s2[:2])
        if score_3_2 > best_score:
            best_score = score_3_2
            best_combo = ('3_from_S1_2_from_S2', [x[0] for x in q_candidates_s1[:3] + q_candidates_s2[:2]])
            
    # Case 2: 2 from Sec I, 3 from Sec II
    if len(q_candidates_s1) >= 2 and len(q_candidates_s2) >= 3:
        score_2_3 = sum(x[1] for x in q_candidates_s1[:2]) + sum(x[1] for x in q_candidates_s2[:3])
        if score_2_3 > best_score:
            best_score = score_2_3
            best_combo = ('2_from_S1_3_from_S2', [x[0] for x in q_candidates_s1[:2] + q_candidates_s2[:3]])
            
    return {
        'max_legal_score': best_score,
        'is_100m_compliant': best_score >= 100,
        'is_90m_compliant': best_score >= 90,
        'best_combo': best_combo
    }
