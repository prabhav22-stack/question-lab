r"""
ExamForge Engine v3.0 - Layer 4: MILP Set-Cover Optimizer with AND-Gated Short Notes
Author: ExamForge Core Team

Implements Mixed-Integer Linear Programming (MILP) using scipy.optimize.milp:
    Binary Decision Variables:
        - x_u in {0, 1}: unit selection in K-unit portfolio (sum x_u = K)
        - z_{q, t} in {0, 1}: AND-gated short-note question slot (z_{q,t} <= x_{u_a}, z_{q,t} <= x_{u_b})
    Historical Playable Questions:
        - C_t^I = sum_{q in Sec I full} x_{u(q, t)} + sum_{q in Sec I short} z_{q, t}
        - C_t^II = sum_{q in Sec II full} x_{u(q, t)} + sum_{q in Sec II short} z_{q, t}
    Statutory Feasibility & Cushion Constraints:
        - C_t^I + s_t^I >= 2
        - C_t^II + s_t^II >= 2
        - w_t^I <= C_t^I, w_t^I <= 3
        - w_t^II <= C_t^II, w_t^II <= 3
        - w_t^I + w_t^II + s_t^Total >= target_cushion (default 5 for statutory 100M, or 6 for cushion)
    Objective:
        Maximize sum S(u, t_next) * x_u - M_statutory * sum(s_t^I + s_t^II) - M_cushion * sum(s_t^Total)
"""

import numpy as np
import pandas as pd
from collections import defaultdict
from scipy.optimize import milp, LinearConstraint, Bounds
from typing import Dict, List, Tuple, Any

class MILPPortfolioOptimizer:
    def __init__(self, total_units: int, k_units: int = 12, m_statutory: float = 100000.0, m_cushion: float = 1000.0, target_cushion: int = 5):
        self.total_units = total_units
        self.k_units = k_units
        self.m_statutory = m_statutory
        self.m_cushion = m_cushion
        self.target_cushion = target_cushion

    def optimize(self, forecast_scores: Dict[int, float], historical_df: pd.DataFrame) -> Dict[str, Any]:
        """
        forecast_scores: dict mapping unit_id (1..total_units) -> composite forecast score S(u, t)
        historical_df: DataFrame containing questions across all historical papers to cover:
            ['paper_id', 'question_number', 'unit', 'marks', ...]
        
        Returns:
            dict containing:
                - 'selected_units': list of 12 units
                - 'core_10': list of top 10 core units
                - 'backup_2': list of 2 supplementary hedge units
                - 'total_slack_sec1': float
                - 'total_slack_sec2': float
                - 'total_slack_cushion': float
                - 'solver_status': str
        """
        papers = list(dict.fromkeys(historical_df['paper_id'].tolist()))
        T = len(papers)
        U = self.total_units

        # Parse questions for each paper
        paper_q_data = []
        all_short_notes = [] # (t_idx, q_num, sec, u_a, u_b)

        for t_idx, pid in enumerate(papers):
            p_df = historical_df[historical_df['paper_id'] == pid]
            sec1_full = []
            sec1_short = []
            sec2_full = []
            sec2_short = []

            for q_num, q_grp in p_df.groupby('question_number'):
                sec = 1 if q_num <= 5 else 2
                if len(q_grp) == 1:
                    u = int(q_grp.iloc[0]['unit'])
                    m = float(q_grp.iloc[0].get('marks', 20))
                    if m >= 20:
                        if sec == 1:
                            sec1_full.append(u)
                        else:
                            sec2_full.append(u)
                elif len(q_grp) == 2:
                    u_a = int(q_grp.iloc[0]['unit'])
                    u_b = int(q_grp.iloc[1]['unit'])
                    if sec == 1:
                        sec1_short.append((u_a, u_b))
                    else:
                        sec2_short.append((u_a, u_b))
                    all_short_notes.append((t_idx, q_num, sec, u_a, u_b))

            paper_q_data.append({
                'paper_id': pid,
                'sec1_full': sec1_full,
                'sec1_short': sec1_short,
                'sec2_full': sec2_full,
                'sec2_short': sec2_short
            })

        Z = len(all_short_notes)
        n_vars = U + Z + 5 * T

        idx_x = lambda u: u - 1
        idx_z = lambda k: U + k
        idx_sI = lambda t: U + Z + t
        idx_sII = lambda t: U + Z + T + t
        idx_sTot = lambda t: U + Z + 2 * T + t
        idx_wI = lambda t: U + Z + 3 * T + t
        idx_wII = lambda t: U + Z + 4 * T + t

        # Build Objective vector (minimization)
        c = np.zeros(n_vars)
        for u in range(1, U + 1):
            c[idx_x(u)] = -forecast_scores.get(u, 0.0)
        for t in range(T):
            c[idx_sI(t)] = self.m_statutory
            c[idx_sII(t)] = self.m_statutory
            c[idx_sTot(t)] = self.m_cushion

        # Integrality: 1 for binary/int, 0 for continuous
        integrality = np.zeros(n_vars)
        for u in range(1, U + 1):
            integrality[idx_x(u)] = 1
        for k in range(Z):
            integrality[idx_z(k)] = 1

        # Variable Bounds
        lb = np.zeros(n_vars)
        ub = np.full(n_vars, np.inf)
        for u in range(1, U + 1):
            ub[idx_x(u)] = 1.0
        for k in range(Z):
            ub[idx_z(k)] = 1.0
        for t in range(T):
            ub[idx_wI(t)] = 3.0
            ub[idx_wII(t)] = 3.0

        bounds = Bounds(lb, ub)

        # Build Constraints
        rows = []
        lhs = []
        rhs = []

        # 1. Portfolio Size: sum x_u == K
        row_k = np.zeros(n_vars)
        for u in range(1, U + 1):
            row_k[idx_x(u)] = 1.0
        rows.append(row_k)
        lhs.append(float(self.k_units))
        rhs.append(float(self.k_units))

        # 2. Short-note AND Gates: z_k <= x_{u_a} and z_k <= x_{u_b}
        for k, (t, q_num, sec, u_a, u_b) in enumerate(all_short_notes):
            row_a = np.zeros(n_vars)
            row_a[idx_z(k)] = 1.0
            row_a[idx_x(u_a)] = -1.0
            rows.append(row_a)
            lhs.append(-np.inf)
            rhs.append(0.0)

            row_b = np.zeros(n_vars)
            row_b[idx_z(k)] = 1.0
            row_b[idx_x(u_b)] = -1.0
            rows.append(row_b)
            lhs.append(-np.inf)
            rhs.append(0.0)

        # Map short notes per paper and section
        short_map = defaultdict(lambda: defaultdict(list))
        for k, (t, q_num, sec, u_a, u_b) in enumerate(all_short_notes):
            short_map[t][sec].append(k)

        # 3. Statutory & Cushion constraints for each paper t
        for t in range(T):
            p = paper_q_data[t]

            # C_t^I + s_I_t >= 2
            row_c1 = np.zeros(n_vars)
            for u in p['sec1_full']:
                row_c1[idx_x(u)] += 1.0
            for k in short_map[t][1]:
                row_c1[idx_z(k)] += 1.0
            row_c1[idx_sI(t)] = 1.0
            rows.append(row_c1)
            lhs.append(2.0)
            rhs.append(np.inf)

            # C_t^II + s_II_t >= 2
            row_c2 = np.zeros(n_vars)
            for u in p['sec2_full']:
                row_c2[idx_x(u)] += 1.0
            for k in short_map[t][2]:
                row_c2[idx_z(k)] += 1.0
            row_c2[idx_sII(t)] = 1.0
            rows.append(row_c2)
            lhs.append(2.0)
            rhs.append(np.inf)

            # w_I_t <= C_t^I  =>  w_I_t - C_t^I <= 0
            row_w1 = np.zeros(n_vars)
            row_w1[idx_wI(t)] = 1.0
            for u in p['sec1_full']:
                row_w1[idx_x(u)] -= 1.0
            for k in short_map[t][1]:
                row_w1[idx_z(k)] -= 1.0
            rows.append(row_w1)
            lhs.append(-np.inf)
            rhs.append(0.0)

            # w_II_t <= C_t^II => w_II_t - C_t^II <= 0
            row_w2 = np.zeros(n_vars)
            row_w2[idx_wII(t)] = 1.0
            for u in p['sec2_full']:
                row_w2[idx_x(u)] -= 1.0
            for k in short_map[t][2]:
                row_w2[idx_z(k)] -= 1.0
            rows.append(row_w2)
            lhs.append(-np.inf)
            rhs.append(0.0)

            # w_I_t + w_II_t + s_Tot_t >= target_cushion
            row_tot = np.zeros(n_vars)
            row_tot[idx_wI(t)] = 1.0
            row_tot[idx_wII(t)] = 1.0
            row_tot[idx_sTot(t)] = 1.0
            rows.append(row_tot)
            lhs.append(float(self.target_cushion))
            rhs.append(np.inf)

        A = np.array(rows)
        constraints = LinearConstraint(A, lhs, rhs)

        # Solve MILP
        res = milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints)

        if not res.success:
            raise RuntimeError(f"MILP failed to converge: {res.message}")

        sol = res.x
        selected_units = sorted([u for u in range(1, U + 1) if sol[idx_x(u)] > 0.5])
        
        # Partition into Core 10 and Backup 2 based on forecast score S(u)
        sorted_by_score = sorted(selected_units, key=lambda u: forecast_scores.get(u, 0.0), reverse=True)
        core_10 = sorted(sorted_by_score[:10])
        backup_2 = sorted(sorted_by_score[10:])

        tot_sI = float(sum(sol[idx_sI(t)] for t in range(T)))
        tot_sII = float(sum(sol[idx_sII(t)] for t in range(T)))
        tot_sTot = float(sum(sol[idx_sTot(t)] for t in range(T)))

        return {
            'selected_units': selected_units,
            'core_10': core_10,
            'backup_2': backup_2,
            'total_slack_sec1': round(tot_sI, 2),
            'total_slack_sec2': round(tot_sII, 2),
            'total_slack_cushion': round(tot_sTot, 2),
            'solver_status': res.message
        }
