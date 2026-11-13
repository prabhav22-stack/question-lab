r"""
ExamForge Engine v3.0 - Layer 2: Hierarchical Block-Pooling & Intra-Block Substitution Boost
Author: ExamForge Core Team

Implements the Upgraded Forecasting Equation:
    S(u, t) = alpha * B_u + beta * M_u(t) - gamma * delta_u(t) + lambda * A_u + eta * Phi_{b(u)}(t)

Where:
    - B_u: Historical baseline appearance frequency up to session t-1
    - M_u(t): Recency momentum (exponentially weighted moving average of recent appearances)
    - delta_u(t): Cooldown indicator (1.0 if appeared in session t-1, 0.5 if short-note, else 0.0)
    - A_u: Slot anchoring concentration score (max slot appearance probability)
    - Phi_{b(u)}(t): Intra-Block Substitution Boost:
          Phi_{b(u)}(t) = B_bar_b * (1 - delta_u(t)) * ( sum_{v in b \ {u}} delta_v(t) / (|b| - 1) )
          where B_bar_b is the historical expected question quota for Block b.
"""

import numpy as np
import pandas as pd
from collections import defaultdict

DEFAULT_WEIGHTS = {
    'alpha': 0.35,   # Baseline frequency
    'beta': 0.25,    # Recency momentum
    'gamma': 0.20,   # Cooldown damper
    'lambda_': 0.10, # Slot anchoring concentration
    'eta': 0.15      # Intra-block substitution boost
}

class Layer2Forecaster:
    def __init__(self, block_map: dict, total_units: int, weights: dict = None):
        """
        block_map: dict mapping unit_id (int) -> block_id (int)
        total_units: total number of syllabus units
        weights: dict of hyperparameters (alpha, beta, gamma, lambda_, eta)
        """
        self.block_map = block_map
        self.total_units = total_units
        self.weights = weights or DEFAULT_WEIGHTS
        
        # Build block to units mapping
        self.block_to_units = defaultdict(list)
        for u in range(1, total_units + 1):
            b = self.block_map.get(u, 1)
            self.block_to_units[b].append(u)

    def forecast_session(self, history_df: pd.DataFrame, target_session: str = None) -> pd.DataFrame:
        """
        history_df: DataFrame of question records with columns:
            ['paper_id', 'question_number', 'unit', 'marks', ...]
        target_session: string identifier for target paper (e.g. '2026_DEC' or a historical paper).
            If historical, history_df should only include papers PRIOR to target_session.
        
        Returns:
            DataFrame indexed by unit (1..total_units) with columns:
            ['unit', 'block', 'B_u', 'M_u', 'delta_u', 'A_u', 'Phi_b', 'S_u']
        """
        # Unique chronological papers in history
        papers = list(dict.fromkeys(history_df['paper_id'].tolist()))
        num_papers = len(papers)
        
        records = []
        
        if num_papers == 0:
            # Cold start prior
            for u in range(1, self.total_units + 1):
                b = self.block_map.get(u, 1)
                records.append({
                    'unit': u, 'block': b,
                    'B_u': 0.5, 'M_u': 0.5, 'delta_u': 0.0,
                    'A_u': 0.2, 'Phi_b': 0.0, 'S_u': 0.5
                })
            return pd.DataFrame(records).set_index('unit')

        last_paper = papers[-1]
        
        # 1. Compute unit appearances per paper
        # Matrix: paper x unit (value = 1 if unit appeared as 20M, 0.5 if 10M, sum capped at 1.0)
        app_matrix = {p: defaultdict(float) for p in papers}
        slot_counts = defaultdict(lambda: defaultdict(int)) # unit -> slot -> count
        block_counts = defaultdict(lambda: defaultdict(float)) # paper -> block -> total_appearances

        for _, row in history_df.iterrows():
            p = row['paper_id']
            u = int(row['unit'])
            m = float(row.get('marks', 20))
            qno = int(row.get('question_number', 1))
            
            w = 1.0 if m >= 20 else 0.5
            app_matrix[p][u] = min(1.0, app_matrix[p][u] + w)
            slot_counts[u][qno] += 1
            
            b = self.block_map.get(u, 1)
            block_counts[p][b] += w

        # 2. Compute Expected Block Quotas B_bar_b
        b_bar = {}
        for b in self.block_to_units.keys():
            total_b_in_history = sum(block_counts[p][b] for p in papers)
            b_bar[b] = total_b_in_history / float(num_papers)

        # 3. Compute delta_u from last session (session t-1)
        deltas = {}
        for u in range(1, self.total_units + 1):
            # 1.0 if appeared full, 0.5 if short note
            deltas[u] = app_matrix[last_paper].get(u, 0.0)

        # 4. Compute each unit's metrics
        alpha = self.weights['alpha']
        beta = self.weights['beta']
        gamma = self.weights['gamma']
        lam = self.weights['lambda_']
        eta = self.weights['eta']

        # Exponential recency weights for last up to 6 papers
        recent_window = min(6, num_papers)
        decay_weights = np.array([0.85 ** i for i in range(recent_window)])
        decay_weights /= decay_weights.sum()

        for u in range(1, self.total_units + 1):
            b = self.block_map.get(u, 1)
            b_units = self.block_to_units[b]
            
            # Baseline B_u (Laplace smoothed appearance rate)
            total_apps = sum(app_matrix[p].get(u, 0.0) for p in papers)
            B_u = (total_apps + 0.5) / (num_papers + 1.0)
            
            # Momentum M_u (weighted recent appearances)
            recent_papers = papers[-recent_window:]
            recent_vals = np.array([app_matrix[p].get(u, 0.0) for p in reversed(recent_papers)])
            M_u = float(np.sum(recent_vals * decay_weights))
            
            # Cooldown delta_u
            delta_u = deltas[u]
            
            # Slot anchoring concentration A_u (max slot probability)
            tot_q_count = sum(slot_counts[u].values())
            if tot_q_count > 0:
                A_u = max(slot_counts[u].values()) / float(tot_q_count)
            else:
                A_u = 0.2
            
            # Intra-Block Substitution Boost Phi_{b(u)}(t)
            # Phi = B_bar_b * (1 - delta_u) * ( sum_{v in b \ {u}} delta_v / (|b| - 1) )
            if len(b_units) > 1:
                sibling_deltas = sum(deltas[v] for v in b_units if v != u)
                frac_sibling_cooldown = sibling_deltas / float(len(b_units) - 1)
                Phi_b = b_bar[b] * (1.0 - delta_u) * frac_sibling_cooldown
            else:
                Phi_b = 0.0

            # Composite Score S(u, t)
            S_raw = alpha * B_u + beta * M_u - gamma * delta_u + lam * A_u + eta * Phi_b
            # Bounded in [0.01, 0.99]
            S_u = float(np.clip(S_raw, 0.01, 0.99))
            
            records.append({
                'unit': u,
                'block': b,
                'B_u': round(B_u, 4),
                'M_u': round(M_u, 4),
                'delta_u': round(delta_u, 2),
                'A_u': round(A_u, 4),
                'Phi_b': round(Phi_b, 4),
                'S_u': round(S_u, 4)
            })

        df_res = pd.DataFrame(records).set_index('unit')
        return df_res
