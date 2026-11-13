"""
ExamForge Engine v3.1 - Production Pipeline & Chronological Walk-Forward Audit
Covers all four courses: MPA-011, MPA-012, MPA-013, MPA-014
Evaluates 4 Architectural Configurations across 2021-2026 Walk-Forward:
Config 1: v3.0 Baseline (15yr baseline, flat cooldown, standard MILP)
Config 2: v3.1 + Format/OCR Fixes Only
Config 3: v3.1 + 5-Yr Window (Ablating No Cooldown vs Beta-Binomial Cooldown)
Config 4: v3.1 + Joint 10-Core & 2-Buffer MILP
"""

import sys
import os
import json
import numpy as np
import pandas as pd
from collections import defaultdict

# Add workspace to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from models.layer1_format_parser import classify_question_format_and_marks, normalize_thinker_aliases
from models.layer2_forecasting_v31 import Layer2ForecasterV31
from models.layer4_joint_optimizer import Joint10Core2BufferOptimizer
from models.layer5_simulator_v31 import score_paper_realistic
from models.tma_topic_signal import get_tma_signal, get_tma_subtopics, CURRENT_CYCLE_TMA_QUESTIONS
from shared.canonical_syllabus_registry.registry import CanonicalSyllabusRegistry

registry = CanonicalSyllabusRegistry()

COURSES = [
    ('MPA-011', 'research/mpa011_forecasting/data/questions_master_v3.csv', 21),
    ('MPA-012', 'research/mpa012_forecasting/data/questions_master_v3.csv', 22),
    ('MPA-013', 'research/mpa013_forecasting/data/questions_master_v3.csv', 25),
    ('MPA-014', 'research/mpa014_forecasting/data/questions_master_v3.csv', 23),
]

def load_and_parse_course_data(course_code: str, fpath: str):
    df = pd.read_csv(fpath)
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    
    # Audit format and apply OCR normalization
    parsed_records = []
    for idx, r in df.iterrows():
        raw_text = str(r['question_text_clean'])
        norm_text, alias_logs = normalize_thinker_aliases(raw_text)
        
        # Classify format
        fmt_info = classify_question_format_and_marks(raw_text)
        
        parsed_records.append({
            'paper_id': r['paper_id'],
            'year': r['year'],
            'section': r['section'],
            'question_number': int(r['question_number']),
            'subpart': r['subpart'] if pd.notna(r['subpart']) else None,
            'unit': int(r['unit']) if pd.notna(r['unit']) else -1,
            'marks': fmt_info['total_marks'] if pd.isna(r['subpart']) else fmt_info['subpart_marks'],
            'format': fmt_info['format'],
            'marks_tier': fmt_info['marks_tier'],
            'normalized_text': norm_text,
            'has_alias_replacement': len(alias_logs) > 0
        })
    return pd.DataFrame(parsed_records)

def structure_paper_questions(paper_df: pd.DataFrame) -> list:
    """
    Groups subparts into numbered question slots (1 to 10)
    """
    structured = []
    for q_num in sorted(paper_df['question_number'].unique()):
        q_rows = paper_df[paper_df['question_number'] == q_num]
        sec = q_rows['section'].iloc[0]
        if len(q_rows) == 1:
            u = q_rows['unit'].iloc[0]
            fmt = 'FULL_20M'
            u_list = [u]
        else:
            fmt = 'SPLIT_10_10'
            u_list = q_rows['unit'].dropna().astype(int).tolist()
        structured.append({
            'question_number': q_num,
            'section': sec,
            'format': fmt,
            'units': u_list
        })
    return structured

def run_chronological_walk_forward():
    print('Starting Chronological Walk-Forward Audit (June 2021 to June 2026)...')
    all_ablation_results = []
    format_audit_rows = []
    
    # Destination outputs
    out_dir = os.path.join(os.path.dirname(__file__), '../outputs')
    os.makedirs(out_dir, exist_ok=True)
    
    for course_code, fpath, tot_units in COURSES:
        print(f'\n================ Processing {course_code} ================')
        parsed_df = load_and_parse_course_data(course_code, fpath)
        
        # Build block map and nominal sections from canonical registry
        units_list = registry.get_units_by_course(course_code)
        block_map = {int(u['unit_number']): int(u['block_number']) for u in units_list}
        
        # Derive empirical section assignments
        s1_units = []
        s2_units = []
        for u in range(1, tot_units + 1):
            udf = parsed_df[parsed_df['unit'] == u]
            if len(udf) == 0:
                # Fallback to nominal section from registry
                nom_sec = units_list[u - 1].get('nominal_section', 'Section I')
                if nom_sec == 'Section I' or u <= (tot_units // 2):
                    s1_units.append(u)
                else:
                    s2_units.append(u)
            else:
                s1_cnt = len(udf[udf['section'] == 'Section I'])
                s2_cnt = len(udf[udf['section'] == 'Section II'])
                if s1_cnt >= s2_cnt:
                    s1_units.append(u)
                else:
                    s2_units.append(u)
                    
        # All test sessions from 2021 onwards
        all_papers = parsed_df['paper_id'].drop_duplicates().tolist()
        eval_papers = parsed_df[parsed_df['year'] >= 2021]['paper_id'].drop_duplicates().tolist()
        
        # Record format audit rows
        for p in eval_papers:
            pdf = parsed_df[parsed_df['paper_id'] == p]
            for _, r in pdf.iterrows():
                format_audit_rows.append({
                    'course_code': course_code,
                    'paper_id': p,
                    'year': r['year'],
                    'question_number': r['question_number'],
                    'subpart': r['subpart'],
                    'unit': r['unit'],
                    'format': r['format'],
                    'marks': r['marks'],
                    'marks_tier': r['marks_tier'],
                    'has_alias': r['has_alias_replacement']
                })
                
        # Compare 5 Configurations on the Walk-Forward folds
        configs = [
            ('v3.0 Baseline (15yr, Std Cooldown, Std MILP)', {'5yr': False, 'cooldown': 'standard_v3', 'optimizer': 'v3_std', 'tma': False}),
            ('v3.1 + Format/OCR Fixes Only', {'5yr': False, 'cooldown': 'standard_v3', 'optimizer': 'joint_10_2', 'tma': False}),
            ('v3.1 + 5-Yr Window (No Cooldown)', {'5yr': True, 'cooldown': 'none', 'optimizer': 'joint_10_2', 'tma': False}),
            ('v3.1 + 5-Yr Window (Beta-Binomial Cooldown)', {'5yr': True, 'cooldown': 'beta_binomial', 'optimizer': 'joint_10_2', 'tma': False}),
            ('v3.1 + Joint 10-Core & 2-Buffer + TMA Tie-Breaker', {'5yr': True, 'cooldown': 'beta_binomial', 'optimizer': 'joint_10_2', 'tma': True})
        ]
        
        for cfg_name, cfg in configs:
            scores_list = []
            compliant_100m_cnt = 0
            compliant_90m_cnt = 0
            brier_scores = []
            
            for p in eval_papers:
                # Training history strictly before paper p
                p_idx = all_papers.index(p)
                train_papers = all_papers[:p_idx]
                train_df = parsed_df[parsed_df['paper_id'].isin(train_papers)]
                
                # Forecasting
                forecaster = Layer2ForecasterV31(
                    block_map=block_map,
                    total_units=tot_units,
                    use_5yr_window=cfg['5yr'],
                    cooldown_mode=cfg['cooldown'],
                    tau=6.0 if cfg['5yr'] else 4.0,
                    use_tma_signal=cfg['tma'],
                    course_code=course_code
                )
                forecast_df = forecaster.forecast_session(train_df)
                fc_scores = dict(zip(forecast_df['unit_number'], forecast_df['forecast_score']))
                fc_probs = dict(zip(forecast_df['unit_number'], forecast_df['normalized_prob']))
                
                # True actual units appearing in paper p
                actual_paper_df = parsed_df[parsed_df['paper_id'] == p]
                actual_units = set(actual_paper_df['unit'].dropna().astype(int).unique())
                
                # Brier score on top 10 units predicted vs actual
                for u in range(1, tot_units + 1):
                    p_pred = min(1.0, fc_probs.get(u, 0.0) * 10.0) # scaled probability of appearance
                    y_true = 1.0 if u in actual_units else 0.0
                    brier_scores.append((p_pred - y_true) ** 2)
                    
                # Portfolio Optimization
                if cfg['optimizer'] == 'v3_std':
                    # Standard greedy top 5 S1 and top 5 S2 without buffer
                    s1_sorted = sorted([u for u in s1_units if 1 <= u <= tot_units], key=lambda u: fc_scores.get(u, 0), reverse=True)
                    s2_sorted = sorted([u for u in s2_units if 1 <= u <= tot_units], key=lambda u: fc_scores.get(u, 0), reverse=True)
                    core_units = set(s1_sorted[:5] + s2_sorted[:5])
                    buf_s1, buf_s2 = None, None
                else:
                    opt = Joint10Core2BufferOptimizer(tot_units, s1_units, s2_units, target_core=10)
                    res_opt = opt.optimize_joint_portfolio(fc_scores, train_df)
                    core_units = set(res_opt['core_units'])
                    buf_s1 = res_opt['buffer_sec1']
                    buf_s2 = res_opt['buffer_sec2']
                    
                # Realistic Scoring
                structured_q = structure_paper_questions(actual_paper_df)
                eval_score = score_paper_realistic(core_units, buf_s1, buf_s2, structured_q)
                
                score = eval_score['max_legal_score']
                scores_list.append(score)
                if eval_score['is_100m_compliant']:
                    compliant_100m_cnt += 1
                if eval_score['is_90m_compliant']:
                    compliant_90m_cnt += 1
                    
            mean_score = np.mean(scores_list)
            min_score = np.min(scores_list)
            sat_rate = (compliant_100m_cnt / len(eval_papers)) * 100.0
            sat_90_rate = (compliant_90m_cnt / len(eval_papers)) * 100.0
            mean_brier = np.mean(brier_scores)
            
            all_ablation_results.append({
                'course_code': course_code,
                'configuration': cfg_name,
                'total_test_papers': len(eval_papers),
                'brier_score': round(mean_brier, 4),
                'mean_attemptable_marks': round(mean_score, 2),
                'min_attemptable_marks': int(min_score),
                'statutory_100m_rate_pct': round(sat_rate, 1),
                'statutory_ge_90m_rate_pct': round(sat_90_rate, 1)
            })
            print(f'  {cfg_name}:')
            print(f'    100M Rate: {sat_rate:5.1f}% | >=90M Rate: {sat_90_rate:5.1f}% | Mean: {mean_score:.1f}M | Min: {min_score}M | Brier: {mean_brier:.4f}')

    # Save outputs
    ablation_df = pd.DataFrame(all_ablation_results)
    ablation_df.to_csv(os.path.join(out_dir, 'v31_feature_ablation.csv'), index=False)
    
    format_audit_df = pd.DataFrame(format_audit_rows)
    format_audit_df.to_csv(os.path.join(out_dir, 'question_format_and_marks_audit.csv'), index=False)
    print('\nSaved v31_feature_ablation.csv and question_format_and_marks_audit.csv')

if __name__ == '__main__':
    run_chronological_walk_forward()
