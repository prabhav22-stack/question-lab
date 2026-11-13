import os
import sys
import re
import math
from collections import Counter
from pathlib import Path

# Common administrative stop words and command words to suppress in clustering
STOP_WORDS = {
    'discuss', 'examine', 'explain', 'critically', 'analyse', 'analyze', 'evaluate', 'elucidate',
    'describe', 'bring', 'out', 'write', 'note', 'short', 'notes', 'following', 'what', 'why',
    'how', 'comment', 'nature', 'scope', 'significance', 'importance', 'meaning', 'concept',
    'features', 'characteristics', 'role', 'context', 'india', 'administration', 'public',
    'management', 'system', 'systems', 'the', 'and', 'for', 'with', 'that', 'from', 'this',
    'these', 'those', 'are', 'was', 'were', 'has', 'have', 'had', 'been', 'its', 'their', 'such'
}

# Key administrative thinkers and concept keywords to preserve as high-weight tokens
THINKER_KEYWORDS = {
    'taylor', 'weber', 'fayol', 'gulick', 'urwick', 'mayo', 'simon', 'maslow', 'herzberg',
    'mcgregor', 'vroom', 'easton', 'barnard', 'riggs', 'waldo', 'marini', 'ostrom', 'senge',
    'follett', 'appleby', 'marx', 'marxist', 'gandhi', 'gandhian', 'swaraj', 'sala', 'prismatic',
    'posdcorb', 'hawthorne', 'bounded', 'satisficing', 'hygiene', 'motivator', 'theory x',
    'theory y', 'valence', 'expectancy', 'zone of indifference', 'cooperative', 'bureaucracy',
    'ideal type', 'minnowbrook', 'new public administration', 'new public management',
    'reinventing government', 'good governance', 'citizen charter', 'right to information',
    'rti', 'whistleblower', 'civil society', 'ngo', 'self help group', 'shg', 'tqm', 'quality circle',
    'performance appraisal', '360 degree', 'acr', 'apar', 'recruitment', 'selection', 'upsc',
    'job description', 'job specification', 'job enrichment', 'job enlargement', 'training needs assessment',
    'tna', 'delphi', 'scenario planning', 'zero base budgeting', 'zbb', 'performance budgeting',
    'materials management', 'inventory control', 'supply chain', 'collective bargaining',
    'grievance redressal', 'industrial relations', 'human resource audit', 'hr audit'
}

def tokenize(text):
    text = text.lower()
    # Normalize aliases
    text = re.sub(r'\bf\.?\s*w\.?\s*taylor\b', 'taylor', text)
    text = re.sub(r'\bchester\s*b[ae]rnard\b', 'barnard', text)
    text = re.sub(r'\bherbert\s*(a\.)?\s*simon\b', 'simon', text)
    text = re.sub(r'\belton\s*mayo\b', 'mayo', text)
    text = re.sub(r'\babraham\s*maslow\b', 'maslow', text)
    text = re.sub(r'\bfrederick\s*herzberg\b', 'herzberg', text)
    text = re.sub(r'\bdouglas\s*mcgregor\b', 'mcgregor', text)
    text = re.sub(r'\bvictor\s*vroom\b', 'vroom', text)
    text = re.sub(r'\bdavid\s*easton\b', 'easton', text)
    text = re.sub(r'\bfred\s*riggs\b', 'riggs', text)
    text = re.sub(r'\bmk\s*gandhi\b', 'gandhi', text)
    text = re.sub(r'\bmahatma\s*gandhi\b', 'gandhi', text)
    
    words = re.findall(r'[a-z0-9]+', text)
    filtered = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    return filtered

def compute_cosine_similarity(tokens1, tokens2):
    c1 = Counter(tokens1)
    c2 = Counter(tokens2)
    all_words = set(c1.keys()).union(set(c2.keys()))
    if not all_words:
        return 0.0
    dot_product = sum(c1.get(w, 0) * c2.get(w, 0) for w in all_words)
    norm1 = math.sqrt(sum(v**2 for v in c1.values()))
    norm2 = math.sqrt(sum(v**2 for v in c2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

def extract_thinkers_and_concepts(text):
    text_lower = text.lower()
    found = []
    for kw in THINKER_KEYWORDS:
        if kw in text_lower:
            found.append(kw)
    return set(found)

def cluster_questions_for_unit(unit_records, similarity_threshold=0.35):
    """
    Cluster questions within one analytical unit.
    Returns a list of clusters, where each cluster is:
    {
        'cluster_id': str,
        'cluster_title': str,
        'cluster_description': str,
        'records': list of question dicts,
        'shared_concepts': list of str,
        'confidence': float,
        'review_flag': str
    }
    """
    if not unit_records:
        return []
        
    clusters = []
    
    # Process records sequentially with deterministic sorting by (year, paper_id, q_num)
    sorted_records = sorted(
        unit_records,
        key=lambda x: (x.get("exam_year", 0), x.get("raw_paper_id", ""), x.get("question_number", ""))
    )
    
    for r in sorted_records:
        q_text = r["question_text"]
        q_tokens = tokenize(q_text)
        q_concepts = extract_thinkers_and_concepts(q_text)
        
        best_cluster = None
        best_sim = 0.0
        
        for c in clusters:
            # Check concept match first
            c_concepts = c["all_concepts"]
            common_concepts = q_concepts.intersection(c_concepts)
            
            # Compute token similarity against all questions in cluster
            sims = [compute_cosine_similarity(q_tokens, tokenize(cr["question_text"])) for cr in c["records"]]
            avg_sim = sum(sims) / len(sims)
            
            # Concept bonus
            if common_concepts:
                # If they share specific named concepts/thinkers, boost similarity
                score = avg_sim + 0.35
            else:
                score = avg_sim
                
            if score > best_sim and score >= similarity_threshold:
                best_sim = score
                best_cluster = c
                
        if best_cluster:
            best_cluster["records"].append(r)
            best_cluster["all_concepts"].update(q_concepts)
        else:
            # Create new cluster
            new_c = {
                "records": [r],
                "all_concepts": set(q_concepts),
                "created_with": q_text
            }
            clusters.append(new_c)
            
    # Assign deterministic cluster IDs, titles, and descriptions
    c_unit_id = unit_records[0]["analytical_unit_id"]
    final_clusters = []
    
    # Sort clusters by size descending, then most recent year descending
    clusters.sort(
        key=lambda c: (len(c["records"]), max(r["exam_year"] for r in c["records"])),
        reverse=True
    )
    
    for idx, c in enumerate(clusters, 1):
        cluster_id = f"{c_unit_id}_C{idx:02d}"
        recs = c["records"]
        
        # Derive representative title
        concepts = sorted(list(c["all_concepts"]))
        if concepts:
            title = " & ".join(w.title() for w in concepts[:3])
            # Add context if short
            if len(title) < 15:
                # pick key noun phrase from most recent question
                recent_q = max(recs, key=lambda x: x["exam_year"])["question_text"]
                clean_q = re.sub(r'^(Discuss|Explain|Examine|Critically analyze|Critically examine|Write a note on)\s+', '', recent_q, flags=re.I)
                title = f"{title}: {clean_q[:40]}..."
        else:
            # Derive title from most recent question text
            recent_q = max(recs, key=lambda x: x["exam_year"])["question_text"]
            clean_q = re.sub(r'^(Discuss|Explain|Examine|Critically analyze|Critically examine|Write a note on|Elucidate)\s+', '', recent_q, flags=re.I).strip()
            # take first 8 words
            w_list = clean_q.split()
            title = " ".join(w_list[:7]).rstrip(",.:;")
            
        desc = f"Historical examination questions on {title.lower()} spanning {len(recs)} questions from {min(r['exam_year'] for r in recs)} to {max(r['exam_year'] for r in recs)}."
        
        final_clusters.append({
            "cluster_id": cluster_id,
            "cluster_title": title,
            "cluster_description": desc,
            "records": recs,
            "shared_concepts": concepts,
            "confidence": 0.92 if len(concepts) > 0 else 0.85,
            "review_flag": "MANUAL_REVIEW_SUGGESTED" if len(recs) == 1 else "VERIFIED"
        })
        
    return final_clusters
