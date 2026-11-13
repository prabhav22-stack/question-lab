import sys, os
sys.path.insert(0, os.path.abspath('.'))
import pandas as pd
from engine_v3.layer1_classifier import classify_mpa011, classify_mpa012, classify_mpa013, classify_mpa014

courses = [
    ('mpa011', classify_mpa011),
    ('mpa012', classify_mpa012),
    ('mpa013', classify_mpa013),
    ('mpa014', classify_mpa014)
]

for course, fn in courses:
    df = pd.read_csv(f"research/{course}_forecasting/data/questions_master.csv")
    assigned = [fn(str(row["question_text"]), str(row["paper_id"]), row["question_number"]) for _, row in df.iterrows()]
    df["unit_v3"] = assigned
    grp = df.groupby(["paper_id", "unit_v3"])["marks"].sum()
    max_m = grp.max()
    over30 = grp[grp > 30]
    print(f"{course.upper()}: Total questions = {len(df)}, Max marks per unit/paper = {max_m}, Collisions (>30M) = {len(over30)}")
    assert max_m <= 30, f"CrosswalkCollisionError: {course} has max marks {max_m} > 30!"
print("\nALL 4 COURSES PASSED THE HARD PER-PAPER MARK CAP ASSERTION (<= 30M)!")
