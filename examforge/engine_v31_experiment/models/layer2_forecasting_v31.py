"""
ExamForge Engine v3.1 - Layer 2:
- 5-Year Rolling Window (with wider EWMA half-life tau = 6 sessions)
- Beta-Binomial Persistence Cooldown:
    R_hat_u = (repeats + 2) / (eligible_transitions + 4)
    delta_eff(u, t) = delta(u, t) * (1 - R_hat_u)
- TMA Topic Signal Integration (for Frozen Forecasts and Diagnostics)
"""

import numpy as np
import pandas as pd
from collections import defaultdict
from typing import Dict, Any, List

class Layer2ForecasterV31:
    def __init__(self, block_map: dict, total_units: int, 
                 weights: dict = None, 
                 use_5yr_window: bool = True,
                 cooldown_mode: str = 'beta_binomial', # 'none', 'standard_v3', 'beta_binomial'
                 tau: float = 6.0,
                 use_tma_signal: bool = False,
                 course_code: str = None):
        self.block_map = block_map
        self.total_units = total_units
        self.use_5yr_window = use_5yr_window
        self.cooldown_mode = cooldown_mode
        self.tau = tau
        self.use_tma_signal = use_tma_signal
        self.course_code = course_code
        
        # Calibrated hyperparameter weights
        default_w = {
            'alpha': 0.30,   # Baseline frequency
            'beta': 0.30,    # Recency momentum
            'gamma': 0.20,   # Cooldown damper
            'lambda_': 0.10, # Slot anchoring
            'eta': 0.10,     # Intra-block substitution boost
            'psi': 0.15      # TMA signal (when active)
        }
        self.weights = weights or default_w

    def calculate_persistence_rates(self, history_df: pd.DataFrame) -> Dict[int, float]:
        """
        Estimates consecutive repeat rate using Beta(2, 2) shrinkage:
        R_hat_u = (repeats + 2) / (eligible_transitions + 4)
        """
        papers = history_df['paper_id'].drop_duplicates().tolist()
        r_hat = {}
        for u in range(1, self.total_units + 1):
            appearances = []
            for p in papers:
                pdf = history_df[history_df['paper_id'] == p]
                appearances.append(1 if u in pdf['unit'].values else 0)
                
            if len(appearances) <= 1:
                r_hat[u] = 2.0 / 4.0 # 0.5 prior
                continue
                
            eligible = sum(appearances[:-1])
            repeats = sum([1 for i in range(len(appearances)-1) if appearances[i] == 1 and appearances[i+1] == 1])
            r_hat[u] = (repeats + 2.0) / (eligible + 4.0)
        return r_hat

    def forecast_session(self, history_df: pd.DataFrame, target_session: str = None) -> pd.DataFrame:
        df = history_df.copy()
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        if self.use_5yr_window:
            # We want rolling window of recent history up to target session:
            # If df has >= 2021 data, filter to last 10-12 papers or year >= 2021
            df_recent = df[df['year'] >= 2021].copy()
            if len(df_recent['paper_id'].drop_duplicates()) >= 3:
                df = df_recent
            else:
                # If earlier in walk-forward, take last 10 papers
                all_p = df['paper_id'].drop_duplicates().tolist()
                df = df[df['paper_id'].isin(all_p[-10:])].copy()
            
        papers = df['paper_id'].drop_duplicates().tolist()
        n_papers = len(papers)
        if n_papers == 0:
            return pd.DataFrame({
                'unit_number': list(range(1, self.total_units + 1)),
                'forecast_score': [1.0 / self.total_units] * self.total_units,
                'normalized_prob': [1.0 / self.total_units] * self.total_units
            })
            
        last_paper_id = papers[-1]
        last_paper = df[df['paper_id'] == last_paper_id]
        
        # 1. Baseline frequency B_u
        unit_counts = df.groupby('unit')['paper_id'].nunique().to_dict()
        B_u = {u: unit_counts.get(u, 0) / n_papers for u in range(1, self.total_units + 1)}
        
        # 2. Recency momentum M_u with EWMA half-life tau
        decay = np.exp(-np.log(2) / self.tau)
        weights_per_paper = [decay ** (n_papers - 1 - i) for i in range(n_papers)]
        norm_w = sum(weights_per_paper)
        
        M_u = {}
        for u in range(1, self.total_units + 1):
            w_sum = 0.0
            for i, p in enumerate(papers):
                pdf = df[df['paper_id'] == p]
                if u in pdf['unit'].values:
                    w_sum += weights_per_paper[i]
            M_u[u] = w_sum / norm_w if norm_w > 0 else 0.0
            
        # 3. Cooldown delta_u
        delta_u = {}
        for u in range(1, self.total_units + 1):
            u_last = last_paper[last_paper['unit'] == u]
            if len(u_last) == 0:
                delta_u[u] = 0.0
            else:
                has_sub = u_last['subpart'].notna().any()
                delta_u[u] = 0.5 if has_sub else 1.0
                
        # Modulate cooldown based on mode
        delta_eff = {}
        if self.cooldown_mode == 'none':
            delta_eff = {u: 0.0 for u in range(1, self.total_units + 1)}
        elif self.cooldown_mode == 'standard_v3':
            delta_eff = delta_u
        elif self.cooldown_mode == 'beta_binomial':
            r_hat = self.calculate_persistence_rates(df)
            delta_eff = {u: delta_u[u] * (1.0 - r_hat[u]) for u in range(1, self.total_units + 1)}
            
        # 4. Slot anchoring concentration A_u
        slot_counts = defaultdict(lambda: defaultdict(int))
        for _, r in df.iterrows():
            if pd.notna(r['unit']) and pd.notna(r['question_number']):
                slot_counts[int(r['unit'])][int(r['question_number'])] += 1
        A_u = {}
        for u in range(1, self.total_units + 1):
            tot = sum(slot_counts[u].values())
            A_u[u] = max(slot_counts[u].values()) / tot if tot > 0 else 0.0
            
        # 5. Intra-Block Substitution Boost Phi_b
        block_units = defaultdict(list)
        for u, b in self.block_map.items():
            block_units[b].append(u)
            
        block_historical_quota = {}
        for b, u_list in block_units.items():
            b_cnt = df[df['unit'].isin(u_list)]['paper_id'].count()
            block_historical_quota[b] = b_cnt / n_papers
            
        Phi_b = {}
        for u in range(1, self.total_units + 1):
            b = self.block_map.get(u, 1)
            siblings = [v for v in block_units[b] if v != u]
            if len(siblings) == 0:
                Phi_b[u] = 0.0
            else:
                sibling_cooldown_sum = sum(delta_eff.get(v, 0.0) for v in siblings)
                b_quota = block_historical_quota.get(b, 1.0)
                Phi_b[u] = b_quota * (1.0 - delta_eff[u]) * (sibling_cooldown_sum / len(siblings))
                
        # 6. TMA Signal Term (if active)
        T_u = {u: 0.0 for u in range(1, self.total_units + 1)}
        if self.use_tma_signal and self.course_code:
            from models.tma_topic_signal import get_tma_signal
            for u in range(1, self.total_units + 1):
                T_u[u] = get_tma_signal(self.course_code, u)
                
        # Combine into S_u
        alpha = self.weights['alpha']
        beta = self.weights['beta']
        gamma = self.weights['gamma']
        lam = self.weights['lambda_']
        eta = self.weights['eta']
        psi = self.weights['psi'] if self.use_tma_signal else 0.0
        
        scores = []
        for u in range(1, self.total_units + 1):
            score = (alpha * B_u[u] + 
                     beta * M_u[u] - 
                     gamma * delta_eff[u] + 
                     lam * A_u[u] + 
                     eta * Phi_b[u] + 
                     psi * T_u[u])
            scores.append({
                'unit_number': u,
                'forecast_score': max(0.001, score),
                'B_u': B_u[u],
                'M_u': M_u[u],
                'delta_eff': delta_eff[u],
                'A_u': A_u[u],
                'Phi_b': Phi_b[u],
                'T_u': T_u[u]
            })
            
        res_df = pd.DataFrame(scores)
        tot_s = res_df['forecast_score'].sum()
        if tot_s > 0:
            res_df['normalized_prob'] = res_df['forecast_score'] / tot_s
        else:
            res_df['normalized_prob'] = 1.0 / self.total_units
        return res_df
