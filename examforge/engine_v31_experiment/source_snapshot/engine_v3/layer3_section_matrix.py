r"""
ExamForge Engine v3.0 - Layer 3: Stochastic Section-Boundary Matrix
Author: ExamForge Core Team

Replaces binary section tags with empirical Section-Assignment Probability Tuples:
    p_u^I = (Appearances of u in Q1-Q5) / (Total Appearances of u)
    p_u^II = 1 - p_u^I

Provides functions to compute empirical section probabilities and calculate
expected section coverage for any portfolio P:
    E[Sec I Coverage] = sum_{u in P} S(u, t) * p_u^I
    E[Sec II Coverage] = sum_{u in P} S(u, t) * p_u^II
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple

class StochasticSectionMatrix:
    def __init__(self, total_units: int, nominal_sections: Dict[int, int] = None):
        """
        total_units: total number of syllabus units
        nominal_sections: optional dict mapping unit_id -> nominal section (1 or 2)
        """
        self.total_units = total_units
        self.nominal_sections = nominal_sections or {}

    def compute_matrix(self, questions_df: pd.DataFrame) -> pd.DataFrame:
        """
        questions_df: DataFrame with columns ['question_number', 'unit']
        
        Returns:
            DataFrame indexed by unit (1..total_units) with columns:
            ['p_sec1', 'p_sec2', 'count_sec1', 'count_sec2', 'total_count']
        """
        records = []
        for u in range(1, self.total_units + 1):
            u_df = questions_df[questions_df['unit'] == u]
            n_sec1 = int((u_df['question_number'] <= 5).sum())
            n_sec2 = int((u_df['question_number'] > 5).sum())
            total = n_sec1 + n_sec2
            
            if total > 0:
                p_sec1 = n_sec1 / float(total)
                p_sec2 = n_sec2 / float(total)
            else:
                # Default to nominal section if never observed
                nom = self.nominal_sections.get(u, 1 if u <= (self.total_units // 2) else 2)
                p_sec1 = 1.0 if nom == 1 else 0.0
                p_sec2 = 0.0 if nom == 1 else 1.0

            records.append({
                'unit': u,
                'p_sec1': round(p_sec1, 4),
                'p_sec2': round(p_sec2, 4),
                'count_sec1': n_sec1,
                'count_sec2': n_sec2,
                'total_count': total
            })
            
        return pd.DataFrame(records).set_index('unit')

    @staticmethod
    def expected_section_coverage(portfolio: set, forecast_scores: Dict[int, float], section_probs: pd.DataFrame) -> Tuple[float, float]:
        """
        Calculates E[Sec I Coverage] and E[Sec II Coverage]
        """
        e_sec1 = 0.0
        e_sec2 = 0.0
        for u in portfolio:
            s_u = forecast_scores.get(u, 0.0)
            p1 = section_probs.loc[u, 'p_sec1']
            p2 = section_probs.loc[u, 'p_sec2']
            e_sec1 += s_u * p1
            e_sec2 += s_u * p2
        return round(e_sec1, 3), round(e_sec2, 3)
