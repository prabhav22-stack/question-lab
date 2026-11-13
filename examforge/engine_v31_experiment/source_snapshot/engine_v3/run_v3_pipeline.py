r"""
ExamForge Engine v3.0 - Production Pipeline & Multi-Course Orchestrator
Target Courses: MPA-011, MPA-012, MPA-013, MPA-014
Author: ExamForge Core Team
"""

import sys
import os
import json
import re
import pandas as pd
import numpy as np

# Ensure workspace root is in path
workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

from engine_v3.layer1_classifier import (
    clean_qtext,
    classify_mpa011,
    classify_mpa012,
    classify_mpa013,
    classify_mpa014,
    extract_empirical_subtopics
)
from shared.canonical_syllabus_registry.registry import CanonicalSyllabusRegistry
from engine_v3.layer2_forecasting import Layer2Forecaster
from engine_v3.layer3_section_matrix import StochasticSectionMatrix
from engine_v3.layer4_milp_optimizer import MILPPortfolioOptimizer
from engine_v3.layer5_statutory_simulator import (
    evaluate_statutory_score,
    evaluate_portfolio_on_archive,
    run_expanding_walk_forward
)

COURSE_CONFIG = {
    'mpa011': {
        'code': 'MPA-011',
        'title': 'State, Society and Public Administration',
        'classifier': classify_mpa011,
        'total_units': 21,
        'dir': 'research/mpa011_forecasting'
    },
    'mpa012': {
        'code': 'MPA-012',
        'title': 'Administrative Theory',
        'classifier': classify_mpa012,
        'total_units': 22,
        'dir': 'research/mpa012_forecasting'
    },
    'mpa013': {
        'code': 'MPA-013',
        'title': 'Public Systems Management',
        'classifier': classify_mpa013,
        'total_units': 25,
        'dir': 'research/mpa013_forecasting'
    },
    'mpa014': {
        'code': 'MPA-014',
        'title': 'Human Resource Management',
        'classifier': classify_mpa014,
        'total_units': 23,
        'dir': 'research/mpa014_forecasting'
    }
}

def load_canonical_crosswalk(course_key: str):
    cfg = COURSE_CONFIG[course_key]
    reg = CanonicalSyllabusRegistry()
    units_info = reg.get_units_by_course(cfg['code'])
    
    unit_titles = {}
    block_map = {}
    nominal_sections = {}
    
    for u_info in units_info:
        u = int(u_info['unit_number'])
        unit_titles[u] = str(u_info['official_unit_title']).strip()
        block_map[u] = int(u_info['block_number'])
        
        # Nominal section from registry
        sec_str = str(u_info.get('nominal_section', ''))
        sec_val = 1 if 'I' in sec_str and 'II' not in sec_str else 2
        nominal_sections[u] = sec_val
        
    return unit_titles, block_map, nominal_sections

def run_course_v3(course_key: str):
    cfg = COURSE_CONFIG[course_key]
    print("\n" + "=" * 80)
    print(f"RUNNING EXAMFORGE v3.0 ENGINE: {cfg['code']} - {cfg['title']}")
    print("=" * 80)
    
    # 1. Load Crosswalk & Crosswalk Metadata
    unit_titles, block_map, nominal_sections = load_canonical_crosswalk(course_key)
    total_units = cfg['total_units']
    
    # 2. Ingest and Re-classify Question Master Dataset (Layer 1)
    q_path = os.path.join(cfg['dir'], 'data', 'questions_master.csv')
    df_q = pd.read_csv(q_path)
    print(f"Loaded {len(df_q)} raw question records from {q_path}")
    
    fn_classify = cfg['classifier']
    classified_units = []
    cleaned_texts = []
    
    for _, r in df_q.iterrows():
        txt = str(r['question_text'])
        c_txt = clean_qtext(txt)
        qnum = int(r['question_number'])
        pid = str(r['paper_id'])
        u = fn_classify(txt, pid, qnum)
        classified_units.append(u)
        cleaned_texts.append(c_txt)
        
    df_q['unit'] = classified_units
    df_q['question_text_clean'] = cleaned_texts
    
    # 3. Hard Per-Paper Mark Cap Assertion (Layer 1)
    grp_m = df_q.groupby(['paper_id', 'unit'])['marks'].sum()
    max_m = grp_m.max()
    over30 = grp_m[grp_m > 30]
    print(f"Layer 1 Collision Check: Max Marks/Unit/Paper = {max_m}M. Over-30 Violations = {len(over30)}")
    assert max_m <= 30, f"CrosswalkCollisionError in {cfg['code']}: max marks = {max_m} > 30!"
    print("✓ Hard Collision Assertion Passed (<= 30M per unit per paper).")
    
    # 4. Extract Empirical Subtopics via PYQ Stem Clustering
    subtopics = extract_empirical_subtopics(df_q, unit_col='unit', text_col='question_text_clean', top_n=4)
    
    # 5. Layer 2 Forecasting (Hierarchical Block-Pooling & Intra-Block Substitution Boost)
    forecaster = Layer2Forecaster(block_map=block_map, total_units=total_units)
    fc_df = forecaster.forecast_session(df_q, target_session="2026_DEC")
    scores = fc_df['S_u'].to_dict()
    print(f"Layer 2 Forecasting: Computed composite scores S(u, t_next) for {total_units} units.")
    
    # 6. Layer 3 Stochastic Section-Boundary Matrix
    sec_matrix_engine = StochasticSectionMatrix(total_units=total_units, nominal_sections=nominal_sections)
    sec_matrix = sec_matrix_engine.compute_matrix(df_q)
    
    # 7. Layer 4 MILP Set-Cover Optimization with AND-Gated Short Notes
    optimizer = MILPPortfolioOptimizer(total_units=total_units, k_units=12, target_cushion=5)
    opt_res = optimizer.optimize(scores, df_q)
    
    selected_12 = opt_res['selected_units']
    core_10 = opt_res['core_10']
    backup_2 = opt_res['backup_2']
    
    print(f"Layer 4 MILP Optimizer: Selected 12 Units: {selected_12}")
    print(f"  -> Core 10: {core_10}")
    print(f"  -> Backup 2: {backup_2}")
    print(f"  -> Historical Slacks: Sec I = {opt_res['total_slack_sec1']}, Sec II = {opt_res['total_slack_sec2']}, Cushion = {opt_res['total_slack_cushion']}")
    
    # Expected Section Coverage for Final Portfolio
    exp_s1, exp_s2 = StochasticSectionMatrix.expected_section_coverage(set(selected_12), scores, sec_matrix)
    print(f"  -> Expected Coverage: E[Sec I] = {exp_s1}, E[Sec II] = {exp_s2}")
    
    # 8. Layer 5 Full-Archive Statutory Exam-Hall Simulation
    eval_full = evaluate_portfolio_on_archive(set(selected_12), df_q)
    eval_core = evaluate_portfolio_on_archive(set(core_10), df_q)
    
    comp_full_rate = eval_full['is_100m_compliant'].mean()
    mean_full_score = eval_full['max_legal_score'].mean()
    min_full_score = eval_full['max_legal_score'].min()
    gte80_full_rate = (eval_full['max_legal_score'] >= 80).mean()
    
    print("\nLayer 5 Statutory Archive Evaluation (10+2 Portfolio):")
    print(f"  -> 100M Statutory Compliance Rate: {comp_full_rate:.1%} ({eval_full['is_100m_compliant'].sum()}/{len(eval_full)})")
    print(f"  -> Mean Legal Score: {mean_full_score:.1f} / 100M")
    print(f"  -> Min Legal Score: {min_full_score} / 100M")
    print(f"  -> Papers scoring >= 80M: {gte80_full_rate:.1%}")
    
    # 9. Layer 5 Expanding-Window Chronological Walk-Forward Out-of-Sample Backtesting
    print("\nRunning Chronological Expanding-Window Walk-Forward Backtester (Burn-in = 12 papers)...")
    wf_df = run_expanding_walk_forward(
        questions_df=df_q,
        forecaster_cls=Layer2Forecaster,
        optimizer_cls=MILPPortfolioOptimizer,
        block_map=block_map,
        total_units=total_units,
        burn_in=12,
        k_units=12
    )
    wf_comp_rate = wf_df['is_100m_compliant'].mean()
    wf_mean_score = wf_df['max_legal_score'].mean()
    wf_min_score = wf_df['max_legal_score'].min()
    wf_gte80 = (wf_df['max_legal_score'] >= 80).mean()
    
    print(f"Walk-Forward Out-of-Sample Results ({len(wf_df)} unseen test sessions):")
    print(f"  -> Out-of-Sample 100M Compliance: {wf_comp_rate:.1%} ({wf_df['is_100m_compliant'].sum()}/{len(wf_df)})")
    print(f"  -> Out-of-Sample Mean Legal Score: {wf_mean_score:.1f} / 100M")
    print(f"  -> Out-of-Sample Min Legal Score: {wf_min_score} / 100M")
    print(f"  -> Out-of-Sample >= 80M Rate: {wf_gte80:.1%}")

    # 10. Update Canonical Files
    # Save clean questions_master_v3.csv
    v3_q_path = os.path.join(cfg['dir'], 'data', 'questions_master_v3.csv')
    df_q.to_csv(v3_q_path, index=False)
    print(f"Saved verified collision-free dataset to {v3_q_path}")
    
    return {
        'course_key': course_key,
        'code': cfg['code'],
        'title': cfg['title'],
        'total_units': total_units,
        'unit_titles': unit_titles,
        'block_map': block_map,
        'subtopics': subtopics,
        'forecast_df': fc_df,
        'sec_matrix': sec_matrix,
        'selected_12': selected_12,
        'core_10': core_10,
        'backup_2': backup_2,
        'exp_s1': exp_s1,
        'exp_s2': exp_s2,
        'archive_eval_full': eval_full,
        'archive_eval_core': eval_core,
        'walk_forward_df': wf_df,
        'comp_full_rate': comp_full_rate,
        'mean_full_score': mean_full_score,
        'min_full_score': min_full_score,
        'gte80_full_rate': gte80_full_rate,
        'wf_comp_rate': wf_comp_rate,
        'wf_mean_score': wf_mean_score,
        'wf_min_score': wf_min_score,
        'wf_gte80': wf_gte80
    }

if __name__ == '__main__':
    all_results = {}
    for ckey in ['mpa011', 'mpa012', 'mpa013', 'mpa014']:
        all_results[ckey] = run_course_v3(ckey)
        
    print("\n" + "=" * 80)
    print("EXAMFORGE v3.0 MULTI-COURSE EXECUTION COMPLETE!")
    print("=" * 80)
