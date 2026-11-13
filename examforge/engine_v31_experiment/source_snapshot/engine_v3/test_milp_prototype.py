import sys, os
sys.path.insert(0, os.path.abspath('.'))
from collections import defaultdict
import numpy as np
import pandas as pd
from scipy.optimize import milp, LinearConstraint, Bounds
from engine_v3.layer1_classifier import classify_mpa013
from engine_v3.layer2_forecasting import Layer2Forecaster

# 1. Load data
cw = pd.read_csv('research/mpa013_forecasting/data/syllabus_crosswalk.csv')
bmap = dict(zip(cw['current_unit'], cw['block_number']))

df = pd.read_csv('research/mpa013_forecasting/data/questions_master.csv')
df['unit'] = [classify_mpa013(str(r['question_text']), str(r['paper_id']), r['question_number']) for _, r in df.iterrows()]

total_units = 25
forecaster = Layer2Forecaster(block_map=bmap, total_units=total_units)
fc = forecaster.forecast_session(df)
scores = fc['S_u'].to_dict()

# Papers list
papers = list(dict.fromkeys(df['paper_id'].tolist()))
T = len(papers)

# Map papers to questions structure:
# For each paper t:
# sec1_full: list of units
# sec1_short: list of (u_a, u_b)
# sec2_full: list of units
# sec2_short: list of (u_a, u_b)
paper_q_data = []
all_short_notes = [] # list of (t_idx, q_slot, u_a, u_b)

for t_idx, pid in enumerate(papers):
    p_df = df[df['paper_id'] == pid]
    sec1_full = []
    sec1_short = []
    sec2_full = []
    sec2_short = []
    
    # Group by question_number
    for q_num, q_grp in p_df.groupby('question_number'):
        sec = 1 if q_num <= 5 else 2
        if len(q_grp) == 1:
            u = int(q_grp.iloc[0]['unit'])
            m = float(q_grp.iloc[0]['marks'])
            if m >= 20:
                if sec == 1:
                    sec1_full.append(u)
                else:
                    sec2_full.append(u)
            else:
                # single 10M? (rare, treated as half-question, but earlier we saw all short notes have 2 subparts)
                pass
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

print(f"Total papers: {T}, Total short note questions across archive: {len(all_short_notes)}")

# Variable indexing:
# 1. x_u for u=1..U (indices 0..U-1) [Binary]
# 2. z_k for each short note k=0..Z-1 [Binary]
# 3. s_I_t for t=0..T-1 [Continuous >= 0]
# 4. s_II_t for t=0..T-1 [Continuous >= 0]
# 5. s_Tot_t for t=0..T-1 [Continuous >= 0]
# 6. w_I_t for t=0..T-1 [Continuous >= 0]
# 7. w_II_t for t=0..T-1 [Continuous >= 0]

U = total_units
Z = len(all_short_notes)
n_vars = U + Z + 5 * T

idx_x = lambda u: u - 1
idx_z = lambda k: U + k
idx_sI = lambda t: U + Z + t
idx_sII = lambda t: U + Z + T + t
idx_sTot = lambda t: U + Z + 2*T + t
idx_wI = lambda t: U + Z + 3*T + t
idx_wII = lambda t: U + Z + 4*T + t

# Objective:
# Maximize sum S_u * x_u - M_penalty * sum (s_I + s_II + s_Tot)
# In scipy.optimize.milp, we minimize c^T v
M_statutory = 100000.0
M_cushion = 10.0
c = np.zeros(n_vars)
for u in range(1, U + 1):
    c[idx_x(u)] = -scores[u]
for t in range(T):
    c[idx_sI(t)] = M_statutory
    c[idx_sII(t)] = M_statutory
    c[idx_sTot(t)] = M_cushion

# Integrality:
# 1 for integer/binary, 0 for continuous
integrality = np.zeros(n_vars)
for u in range(1, U + 1):
    integrality[idx_x(u)] = 1
for k in range(Z):
    integrality[idx_z(k)] = 1

# Bounds:
# x_u in [0, 1]
# z_k in [0, 1]
# s_I_t, s_II_t, s_Tot_t in [0, inf)
# w_I_t, w_II_t in [0, 3]
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

# Constraints:
# 1. sum x_u == K (where K = 12)
rows = []
lhs = []
rhs = []

# Portfolio size constraint
row_k = np.zeros(n_vars)
for u in range(1, U + 1):
    row_k[idx_x(u)] = 1.0
rows.append(row_k)
lhs.append(12.0)
rhs.append(12.0)

# Short-note AND gates:
# For each short note k = (t, q_num, sec, u_a, u_b):
# z_k <= x_{u_a}  =>  z_k - x_{u_a} <= 0
# z_k <= x_{u_b}  =>  z_k - x_{u_b} <= 0
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

# Map (t, sec) -> list of z_k indices
short_map = defaultdict(lambda: defaultdict(list))
for k, (t, q_num, sec, u_a, u_b) in enumerate(all_short_notes):
    short_map[t][sec].append(k)

# For each paper t:
# C_t^I = sum_{u in sec1_full} x_u + sum_{k in short_sec1} z_k
# C_t^II = sum_{u in sec2_full} x_u + sum_{k in short_sec2} z_k
for t in range(T):
    p = paper_q_data[t]
    
    # 1. C_t^I + s_I_t >= 2
    row_c1 = np.zeros(n_vars)
    for u in p['sec1_full']:
        row_c1[idx_x(u)] += 1.0
    for k in short_map[t][1]:
        row_c1[idx_z(k)] += 1.0
    row_c1[idx_sI(t)] = 1.0
    rows.append(row_c1)
    lhs.append(2.0)
    rhs.append(np.inf)

    # 2. C_t^II + s_II_t >= 2
    row_c2 = np.zeros(n_vars)
    for u in p['sec2_full']:
        row_c2[idx_x(u)] += 1.0
    for k in short_map[t][2]:
        row_c2[idx_z(k)] += 1.0
    row_c2[idx_sII(t)] = 1.0
    rows.append(row_c2)
    lhs.append(2.0)
    rhs.append(np.inf)

    # 3. w_I_t <= C_t^I  =>  w_I_t - C_t^I <= 0
    row_w1 = np.zeros(n_vars)
    row_w1[idx_wI(t)] = 1.0
    for u in p['sec1_full']:
        row_w1[idx_x(u)] -= 1.0
    for k in short_map[t][1]:
        row_w1[idx_z(k)] -= 1.0
    rows.append(row_w1)
    lhs.append(-np.inf)
    rhs.append(0.0)

    # 4. w_II_t <= C_t^II => w_II_t - C_t^II <= 0
    row_w2 = np.zeros(n_vars)
    row_w2[idx_wII(t)] = 1.0
    for u in p['sec2_full']:
        row_w2[idx_x(u)] -= 1.0
    for k in short_map[t][2]:
        row_w2[idx_z(k)] -= 1.0
    rows.append(row_w2)
    lhs.append(-np.inf)
    rhs.append(0.0)

    # 5. w_I_t + w_II_t + s_Tot_t >= 5 (statutory 5 full questions constraint: 3+2 or 2+3)
    row_tot = np.zeros(n_vars)
    row_tot[idx_wI(t)] = 1.0
    row_tot[idx_wII(t)] = 1.0
    row_tot[idx_sTot(t)] = 1.0
    rows.append(row_tot)
    lhs.append(5.0)
    rhs.append(np.inf)

A = np.array(rows)
constraints = LinearConstraint(A, lhs, rhs)

print(f"Solving MILP with {n_vars} variables and {len(rows)} constraints...")
res = milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints)

print("MILP Status:", res.status, res.message)
if res.success:
    sol = res.x
    selected_units = [u for u in range(1, U + 1) if sol[idx_x(u)] > 0.5]
    print("Selected 12 units:", selected_units)
    tot_sI = sum(sol[idx_sI(t)] for t in range(T))
    tot_sII = sum(sol[idx_sII(t)] for t in range(T))
    tot_sTot = sum(sol[idx_sTot(t)] for t in range(T))
    print(f"Total Slacks: Sec I slack = {tot_sI:.1f}, Sec II slack = {tot_sII:.1f}, Total cushion slack = {tot_sTot:.1f}")

from itertools import combinations

def evaluate_statutory_score(selected_units: set, paper_questions: list) -> dict:
    """
    paper_questions: list of dicts:
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

# Run Statutory Evaluator across all 31 papers
selected_set = set(selected_units)
results = []
for pid in papers:
    p_df = df[df['paper_id'] == pid]
    paper_qs = []
    for q_num, q_grp in p_df.groupby('question_number'):
        sec = 1 if q_num <= 5 else 2
        u_list = [int(u) for u in q_grp['unit'].tolist()]
        paper_qs.append({'q_num': q_num, 'section': sec, 'units': u_list})
    
    ev = evaluate_statutory_score(selected_set, paper_qs)
    ev['paper_id'] = pid
    results.append(ev)

res_df = pd.DataFrame(results)
print("\n=== LAYER 5 STATUTORY EVALUATION ACROSS ALL 31 PAPERS ===")
print(f"Mean Legal Score: {res_df['max_legal_score'].mean():.1f} / 100M")
print(f"Min Legal Score: {res_df['max_legal_score'].min()} / 100M")
print(f"100M Statutory Compliance Rate: {res_df['is_100m_compliant'].mean():.1%} ({res_df['is_100m_compliant'].sum()}/{len(res_df)})")
print(f"Papers scoring >= 80M: {(res_df['max_legal_score'] >= 80).mean():.1%} ({(res_df['max_legal_score'] >= 80).sum()}/{len(res_df)})")
print("\nPapers with max_legal_score < 100:")
for _, r in res_df[res_df['max_legal_score'] < 100].iterrows():
    print(f"  {r['paper_id']}: {r['max_legal_score']}M (Sec I 20M: {r['full_20m_sec1']}, Sec II 20M: {r['full_20m_sec2']}, Chosen: {r['optimal_5_questions']})")


