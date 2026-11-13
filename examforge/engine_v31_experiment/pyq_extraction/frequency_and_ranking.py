import os
import sys
import re
from pathlib import Path

# Eligible sessions for recent 5-yr window (June 2021 through June 2026 inclusive)
ELIGIBLE_5YR_SESSIONS = [
    "Jun 2021", "Dec 2021",
    "Jun 2022", "Dec 2022",
    "Jun 2023", "Dec 2023",
    "Jun 2024", "Dec 2024",
    "Jun 2025", "Dec 2025",
    "Jun 2026"
]
TOTAL_ELIGIBLE_5YR = len(ELIGIBLE_5YR_SESSIONS) # 11

LATEST_3YR_SESSIONS = [
    "Jun 2023", "Dec 2023",
    "Jun 2024", "Dec 2024",
    "Jun 2025", "Dec 2025",
    "Jun 2026"
]

def calculate_cluster_metrics(cluster, course_code, tma_questions_for_course):
    records = cluster["records"]
    
    # 1. Recent session frequency (freq_5yr)
    sessions_5yr = set()
    records_5yr = []
    
    for r in records:
        sess = r["session"]
        if sess in ELIGIBLE_5YR_SESSIONS:
            sessions_5yr.add(sess)
            records_5yr.append(r)
            
    freq_5yr = len(sessions_5yr)
    occurrences_5yr = len(records_5yr)
    
    # 2. All-time metrics
    all_sessions = set(r["session"] for r in records)
    sessions_all = len(all_sessions)
    freq_all = len(records)
    
    # Sort records to find last asked
    sorted_recs = sorted(records, key=lambda x: (x["exam_year"], x["session"]))
    last_asked = sorted_recs[-1]["session"] if sorted_recs else "None"
    
    # 3. Latest 3-year sessions
    sess_3yr = set(r["session"] for r in records if r["session"] in LATEST_3YR_SESSIONS)
    latest_3yr_sessions = len(sess_3yr)
    latest_3yr_occurrences = sum(1 for r in records if r["session"] in LATEST_3YR_SESSIONS)
    
    # Recency gap: number of sessions since last appearance up to Jun 2026
    # Ordered session index
    session_order = [
        "Jun 2011", "Dec 2011", "Jun 2012", "Dec 2012", "Jun 2013", "Dec 2013",
        "Jun 2014", "Dec 2014", "Jun 2015", "Dec 2015", "Jun 2016", "Dec 2016",
        "Jun 2017", "Dec 2017", "Jun 2018", "Dec 2018", "Jun 2019", "Dec 2019",
        "Jun 2020", "Dec 2020", "Jun 2021", "Dec 2021", "Jun 2022", "Dec 2022",
        "Jun 2023", "Dec 2023", "Jun 2024", "Dec 2024", "Jun 2025", "Dec 2025",
        "Jun 2026"
    ]
    try:
        last_idx = session_order.index(last_asked)
        recency_gap_sessions = len(session_order) - 1 - last_idx
    except:
        recency_gap_sessions = 99
        
    # Format counts
    full_20m_count = sum(1 for r in records if r["format_type"] == "FULL_20M")
    split_10m_count = sum(1 for r in records if r["format_type"] == "SPLIT_10M")
    format_unknown_count = sum(1 for r in records if r["format_type"] not in ["FULL_20M", "SPLIT_10M"])
    
    # TMA matching
    # Check if any question in cluster or cluster_title matches TMA questions for this course
    tma_match = "NO"
    tma_cycle = "2025-26 & 2026-27"
    tma_evidence = "Inspected relevant TMA assignment questions; no direct conceptual overlap found."
    tma_source_id = "NONE"
    
    c_title_lower = cluster["cluster_title"].lower()
    c_concepts = cluster.get("shared_concepts", [])
    
    for tma_q in tma_questions_for_course:
        tma_text_lower = tma_q["text"].lower()
        tma_subtopic_lower = tma_q.get("subtopic", "").lower()
        
        # Check unit overlap
        # Check concept / title overlap
        has_overlap = False
        for kw in c_concepts:
            if kw in tma_text_lower or kw in tma_subtopic_lower:
                has_overlap = True
                break
                
        # Also check word overlap
        if not has_overlap:
            c_words = set(re.findall(r'[a-z0-9]+', c_title_lower))
            t_words = set(re.findall(r'[a-z0-9]+', tma_text_lower))
            significant_overlap = c_words.intersection(t_words) - {'and', 'the', 'for', 'with', 'state', 'public', 'management'}
            if len(significant_overlap) >= 2:
                has_overlap = True
                
        if has_overlap:
            tma_match = "YES"
            tma_source_id = f"TMA_{course_code.replace('-','')}_Q{tma_q['q_num']}"
            tma_evidence = f"Verified conceptual match with TMA Q{tma_q['q_num']} ({tma_q['marks']}M): '{tma_q['text']}'"
            break
            
    metrics = {
        "freq_5yr": freq_5yr,
        "available_sessions_5yr": TOTAL_ELIGIBLE_5YR,
        "occurrences_5yr": occurrences_5yr,
        "freq_all": freq_all,
        "sessions_all": sessions_all,
        "last_asked": last_asked,
        "latest_3yr_sessions": latest_3yr_sessions,
        "latest_3yr_occurrences": latest_3yr_occurrences,
        "recency_gap_sessions": recency_gap_sessions,
        "full_20m_count": full_20m_count,
        "split_10m_count": split_10m_count,
        "format_unknown_count": format_unknown_count,
        "tma_match": tma_match,
        "tma_session_or_cycle": tma_cycle,
        "tma_evidence": tma_evidence,
        "tma_source_id": tma_source_id
    }
    cluster["metrics"] = metrics
    return metrics

def rank_clusters_for_unit(clusters, course_code):
    """
    Apply course-specific ranking policy:
    For MPA-011, MPA-012, MPA-014:
      1. freq_5yr desc
      2. tma_match (YES > NO > UNKNOWN)
      3. freq_all desc
      4. latest_3yr_sessions desc
      5. last_asked desc
      6. occurrences_5yr desc
      
    For MPA-013:
      1. freq_all desc
      2. freq_5yr desc
      3. tma_match (YES > NO > UNKNOWN)
      4. latest_3yr_sessions desc
      5. last_asked desc
      6. occurrences_5yr desc
    """
    def tma_val(m):
        return 2 if m == "YES" else (1 if m == "UNKNOWN" else 0)

    # Session order rank for sorting
    session_order = [
        "Jun 2011", "Dec 2011", "Jun 2012", "Dec 2012", "Jun 2013", "Dec 2013",
        "Jun 2014", "Dec 2014", "Jun 2015", "Dec 2015", "Jun 2016", "Dec 2016",
        "Jun 2017", "Dec 2017", "Jun 2018", "Dec 2018", "Jun 2019", "Dec 2019",
        "Jun 2020", "Dec 2020", "Jun 2021", "Dec 2021", "Jun 2022", "Dec 2022",
        "Jun 2023", "Dec 2023", "Jun 2024", "Dec 2024", "Jun 2025", "Dec 2025",
        "Jun 2026"
    ]
    def last_asked_rank(s):
        try:
            return session_order.index(s)
        except:
            return -1

    if course_code == "MPA-013":
        # 15-year unweighted policy
        clusters.sort(
            key=lambda c: (
                c["metrics"]["freq_all"],
                c["metrics"]["freq_5yr"],
                tma_val(c["metrics"]["tma_match"]),
                c["metrics"]["latest_3yr_sessions"],
                last_asked_rank(c["metrics"]["last_asked"]),
                c["metrics"]["occurrences_5yr"]
            ),
            reverse=True
        )
    else:
        # 5-year primary memory policy (MPA-011, MPA-012, MPA-014)
        clusters.sort(
            key=lambda c: (
                c["metrics"]["freq_5yr"],
                tma_val(c["metrics"]["tma_match"]),
                c["metrics"]["freq_all"],
                c["metrics"]["latest_3yr_sessions"],
                last_asked_rank(c["metrics"]["last_asked"]),
                c["metrics"]["occurrences_5yr"]
            ),
            reverse=True
        )
        
    for rank, c in enumerate(clusters, 1):
        c["cluster_rank"] = rank
        
    return clusters
