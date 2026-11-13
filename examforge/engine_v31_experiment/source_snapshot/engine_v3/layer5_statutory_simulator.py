r"""
ExamForge Engine v3.0 - Layer 5: True Statutory Exam-Hall Simulator & Out-of-Sample Backtester
Author: ExamForge Core Team

Implements:
1. Exact IGNOU statutory exam-hall decision simulation:
   - 5 questions chosen out of 10
   - At least 2 from Section I, at least 2 from Section II (3+2 or 2+3 split)
   - 10M + 10M short notes scored accurately (20M if both subparts covered, 10M if one, 0M if neither)
2. Chronological Walk-Forward (expanding window) out-of-sample backtester with zero future lookahead.
"""

from itertools import combinations
import numpy as np
import pandas as pd
from typing import Dict, List, Set, Any

def evaluate_statutory_score(selected_units: set, paper_questions: list) -> dict:
    """
    paper_questions: list of 10 dicts:
      - Full Q (q_num in 1..4, 6..9): {'q_num': 1, 'section': 1, 'units': [u1]}
      - Short Note Q (q_num in 5, 10): {'q_num': 5, 'section': 1, 'units': [u_a, u_b]}
    Returns the exact maximum legal score out of 100 under IGNOU's 5-question (3+2 / 2+3) rule.
    """
    q_scores = {}
    for q in paper_questions:
        u_list = q['units']
        if len(u_list) == 1:
            q_scores[q['q_num']] = 20 if u_list[0] in selected_units else 0
        else:
            # 10M + 10M short note: 20M if both covered, 10M if one covered, 0M if neither
            q_scores[q['q_num']] = 10 * sum(1 for u in u_list if u in selected_units)

    sec1_qs = [q['q_num'] for q in paper_questions if q['section'] == 1]
    sec2_qs = [q['q_num'] for q in paper_questions if q['section'] == 2]

    best_legal_score = 0
    best_combination = ()

    # Legal splits: (3 from Sec I, 2 from Sec II) OR (2 from Sec I, 3 from Sec II)
    for n_sec1, n_sec2 in [(3, 2), (2, 3)]:
        for c1 in combinations(sec1_qs, n_sec1):
            for c2 in combinations(sec2_qs, n_sec2):
                chosen_5 = c1 + c2
                score = sum(q_scores[q_num] for q_num in chosen_5)
                if score > best_legal_score:
                    best_legal_score = score
                    best_combination = chosen_5

    # Count how many full 20M questions are available in each section (for cushion analysis)
    full_20m_sec1 = sum(1 for q in sec1_qs if q_scores[q] == 20)
    full_20m_sec2 = sum(1 for q in sec2_qs if q_scores[q] == 20)

    return {
        "max_legal_score": best_legal_score,          # True score out of 100M
        "is_100m_compliant": best_legal_score == 100, # True only if 5 full 20M Qs are playable
        "full_20m_sec1": full_20m_sec1,
        "full_20m_sec2": full_20m_sec2,
        "total_playable_marks": (full_20m_sec1 + full_20m_sec2) * 20,
        "optimal_5_questions": best_combination
    }

def build_paper_question_list(paper_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Constructs the canonical paper_questions format from a questions DataFrame subset for a single paper.
    """
    paper_qs = []
    for q_num, q_grp in paper_df.groupby('question_number'):
        sec = 1 if q_num <= 5 else 2
        u_list = [int(u) for u in q_grp['unit'].tolist()]
        paper_qs.append({
            'q_num': int(q_num),
            'section': sec,
            'units': u_list
        })
    return paper_qs

def evaluate_portfolio_on_archive(selected_units: Set[int], questions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Evaluates a single fixed portfolio across all papers in questions_df.
    """
    papers = list(dict.fromkeys(questions_df['paper_id'].tolist()))
    results = []
    
    for pid in papers:
        p_df = questions_df[questions_df['paper_id'] == pid]
        p_qs = build_paper_question_list(p_df)
        ev = evaluate_statutory_score(selected_units, p_qs)
        ev['paper_id'] = pid
        results.append(ev)
        
    return pd.DataFrame(results)

def run_expanding_walk_forward(
    questions_df: pd.DataFrame,
    forecaster_cls,
    optimizer_cls,
    block_map: dict,
    total_units: int,
    burn_in: int = 12,
    k_units: int = 12
) -> pd.DataFrame:
    """
    Executes rigorous expanding-window chronological out-of-sample backtesting.
    For each test paper t from burn_in to T:
      - Train window = papers 0 .. t-1
      - Test paper = paper t
    """
    papers = list(dict.fromkeys(questions_df['paper_id'].tolist()))
    T = len(papers)
    wf_results = []

    for t_idx in range(burn_in, T):
        test_pid = papers[t_idx]
        train_pids = papers[:t_idx]
        
        train_df = questions_df[questions_df['paper_id'].isin(train_pids)]
        test_df = questions_df[questions_df['paper_id'] == test_pid]
        
        # 1. Forecast S(u, t) using strictly training data
        fc_engine = forecaster_cls(block_map=block_map, total_units=total_units)
        fc_df = fc_engine.forecast_session(train_df, target_session=test_pid)
        scores = fc_df['S_u'].to_dict()
        
        # 2. Optimize portfolio using strictly training data
        opt_engine = optimizer_cls(total_units=total_units, k_units=k_units)
        opt_res = opt_engine.optimize(scores, train_df)
        selected = set(opt_res['selected_units'])
        
        # 3. Evaluate Out-of-Sample on unseen test paper
        test_qs = build_paper_question_list(test_df)
        ev = evaluate_statutory_score(selected, test_qs)
        
        ev['paper_id'] = test_pid
        ev['step'] = t_idx - burn_in + 1
        ev['train_papers_count'] = len(train_pids)
        ev['selected_portfolio'] = sorted(list(selected))
        wf_results.append(ev)

    return pd.DataFrame(wf_results)
