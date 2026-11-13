import os
import sys
import csv
import json
from pathlib import Path

ROOT = Path("D:/Stuff/ExamForge")
OUTPUT_DIR = ROOT / "engine_v31_experiment/pyq_extraction/outputs"
CSV_PATH = OUTPUT_DIR / "locked_units_clustered_pyqs.csv"
FRAMEWORKS_PATH = OUTPUT_DIR / "answer_frameworks.json"
MODEL_ANSWERS_PATH = OUTPUT_DIR / "model_answers.json"

def generate_markdown_banks():
    print("Generating NotebookLM-ready Markdown study banks with Full Model Answers...")
    
    with open(CSV_PATH, encoding="utf-8") as f:
        records = list(csv.DictReader(f))
        
    frameworks = {}
    if FRAMEWORKS_PATH.exists():
        frameworks = json.load(open(FRAMEWORKS_PATH, encoding="utf-8"))
        
    model_answers = {}
    if MODEL_ANSWERS_PATH.exists():
        model_answers = json.load(open(MODEL_ANSWERS_PATH, encoding="utf-8"))
        
    course_data = {}
    for r in records:
        c_id = r["course_id"]
        if c_id not in course_data:
            course_data[c_id] = {}
            
        a_id = r["analytical_unit_id"]
        if a_id not in course_data[c_id]:
            course_data[c_id][a_id] = {
                "unit_title": r["unit_title"],
                "portfolio_tier": r["portfolio_tier"],
                "section": r["portfolio_section"],
                "clusters": {}
            }
            
        cl_id = r["cluster_id"]
        if cl_id not in course_data[c_id][a_id]["clusters"]:
            course_data[c_id][a_id]["clusters"][cl_id] = {
                "cluster_id": cl_id,
                "cluster_title": r["cluster_title"],
                "cluster_description": r["cluster_description"],
                "cluster_rank": int(r["cluster_rank"]),
                "freq_5yr": int(r["freq_5yr"]),
                "available_sessions_5yr": int(r["available_sessions_5yr"]),
                "occurrences_5yr": int(r["occurrences_5yr"]),
                "freq_all": int(r["freq_all"]),
                "sessions_all": int(r["sessions_all"]),
                "last_asked": r["last_asked"],
                "full_20m_count": int(r["full_20m_count"]),
                "split_10m_count": int(r["split_10m_count"]),
                "tma_match": r["tma_match"],
                "tma_evidence": r["tma_evidence"],
                "questions": []
            }
        course_data[c_id][a_id]["clusters"][cl_id]["questions"].append(r)
        
    course_info = {
        "MPA-011": {
            "title": "State, Society and Public Administration",
            "model": "5-Year Beta-Binomial Recency Prioritised (Full 20M Essay Mode)",
            "memory": "5-Year Primary Memory (June 2021 – June 2026)",
            "desc": "Analysis of the State, civil society, bureaucracy, and public management paradigms."
        },
        "MPA-012": {
            "title": "Administrative Theory",
            "model": "15-Year No-Cooldown Classical Baseline (Split 10M Short Notes Q5 & Q10)",
            "memory": "5-Year Primary Memory for ranking with 15-Year historical baseline",
            "desc": "Classical, human relations, behavioural, systems, and post-modern administrative thought."
        },
        "MPA-013": {
            "title": "Public Systems Management",
            "model": "15-Year Unweighted Stabilized Memory (Retains Unit 25 in Core)",
            "memory": "15-Year Unweighted Primary Memory (June 2011 – June 2026)",
            "desc": "Public governance systems, operations research, accountability, change management, and reforms."
        },
        "MPA-014": {
            "title": "Human Resource Management",
            "model": "5-Year Beta-Binomial Recency Prioritised (Worker Participation Surge)",
            "memory": "5-Year Primary Memory (June 2021 – June 2026)",
            "desc": "Strategic HRM, recruitment, training, performance appraisal, industrial relations, and empowerment."
        }
    }

    for c_id, u_dict in course_data.items():
        info = course_info[c_id]
        md_lines = []
        
        md_lines.append(f"# {c_id}: {info['title']}")
        md_lines.append(f"## December 2026 High-Frequency PYQ Study Bank & Complete Model Answers\n")
        md_lines.append(f"**Course Title:** {info['title']}")
        md_lines.append(f"**Forecasting Architecture:** {info['model']}")
        md_lines.append(f"**Historical Memory Window:** {info['memory']}")
        md_lines.append(f"**Authoritative Sources:** Official IGNOU Ebooks (`MPA-1st Year`), Canonical Registry, Verified PYQ Dataset (2011–2026), and Verified TMA Signals (2025–2027).\n")
        
        md_lines.append("### Methodological & Metric Definitions")
        md_lines.append("- **5-Yr Frequency (`freq_5yr`):** Count of *distinct examination sessions* in which this cluster appeared between June 2021 and June 2026 (Max: 11 sessions).")
        md_lines.append("- **All-Time Occurrences (`freq_all`):** Total count of *distinct historical question occurrences* mapped to this cluster across the complete 15-year dataset (2011–2026).")
        md_lines.append("- **Full Model Answers:** Written in full 500-word essay depth (or 250-word note depth) grounded in official IGNOU ebooks from `MPA-1st Year`.\n")
        md_lines.append("---\n")

        sec1_core = []
        sec2_core = []
        buffers = []

        for a_id, u_data in u_dict.items():
            if u_data["portfolio_tier"] == "10_CORE":
                if u_data["section"] == "Section I":
                    sec1_core.append((a_id, u_data))
                else:
                    sec2_core.append((a_id, u_data))
            else:
                buffers.append((a_id, u_data))
                
        def format_unit_block(a_id, u_data):
            lines = []
            lines.append(f"### Unit {a_id}: {u_data['unit_title']}")
            tier_str = "CORE 10 (Full 500-Word Essay Preparation)" if u_data["portfolio_tier"] == "10_CORE" else "EMERGENCY BUFFER (250-Word Targeted Skeleton)"
            lines.append(f"**Portfolio Designation:** {tier_str} | **Section:** {u_data['section']}\n")
            
            sorted_clusters = sorted(u_data["clusters"].values(), key=lambda x: x["cluster_rank"])
            top_n = 5 if u_data["portfolio_tier"] == "10_CORE" else 2
            selected_clusters = sorted_clusters[:top_n]
            
            lines.append(f"*Displaying Top {len(selected_clusters)} High-Yield Examination Clusters (out of {len(sorted_clusters)} historical clusters)*\n")
            
            for c in selected_clusters:
                cl_id = c["cluster_id"]
                # TMA badge
                tma_badge = "🎯 TMA CONFIRMED" if c['tma_match'] == "YES" else ""
                rank_label = f"Rank {c['cluster_rank']}"
                lines.append(f"#### {rank_label} | {c['cluster_title']} {tma_badge}")
                lines.append(f"`[5-Yr: {c['freq_5yr']}/{c['available_sessions_5yr']} | All-Time: {c['freq_all']} | TMA: {c['tma_match']}]`\n")
                lines.append(f"- **Recent 5-Yr Sessions:** {c['freq_5yr']} sessions ({c['occurrences_5yr']} appearances)")
                lines.append(f"- **Historical Total:** {c['freq_all']} questions across {c['sessions_all']} examination sessions")
                lines.append(f"- **Last Asked Session:** {c['last_asked']}")
                lines.append(f"- **Format Breakdown:** FULL_20M: {c['full_20m_count']} | SPLIT_10M: {c['split_10m_count']}")
                if c['tma_match'] == "YES":
                    lines.append(f"- **🎯 TMA Signal:** {c['tma_evidence']}\n")
                else:
                    lines.append(f"- **TMA Status:** No direct TMA overlap detected\n")

                # Show ALL PYQs for large clusters (>= 8 questions), else top 5
                all_qs = c["questions"]
                show_limit = len(all_qs) if len(all_qs) >= 8 else min(5, len(all_qs))
                lines.append(f"**Verbatim Historical PYQs ({len(all_qs)} total — showing {show_limit}):**")
                sample_qs = all_qs[:show_limit]
                for q in sample_qs:
                    tag = f"[{q['session']} | Q{q['question_number']}{q['subquestion']} | {q['section']} | {q['format_type']} | {q['marks']}M]"
                    lines.append(f"- {tag} {q['question_text']}")
                lines.append("")
                
                # Check for FULL MODEL ANSWER (Rank 1 primary)
                if c['cluster_rank'] == 1 and cl_id in model_answers:
                    ma = model_answers[cl_id]
                    sdata = ma.get("structured_data", {})
                    lines.append("<details open>")
                    lines.append(f"<summary><b>📝 Full-Length Model Answer ({ma.get('format')} | {ma.get('marks')} Marks | {ma.get('word_count_target')})</b></summary>\n")
                    lines.append(f"*Grounded in official IGNOU study materials from `MPA-1st Year` Unit text | Verified via Groq*\n")
                    lines.append(f"**Question:** *\"{ma.get('representative_question')}\"*\n")
                    lines.append(f"**Introduction:**\n{sdata.get('introduction','')}\n")
                    for bsec in sdata.get("body_sections", []):
                        lines.append(f"**{bsec.get('heading','')}**\n{bsec.get('content','')}\n")
                    lines.append(f"**Critical Evaluation & Administrative Relevance:**\n{sdata.get('critical_evaluation','')}\n")
                    lines.append(f"**Conclusion:**\n{sdata.get('conclusion','')}\n")
                    lines.append(f"**Key Thinkers & Concepts:** {', '.join(sdata.get('key_thinkers_cited', []))}\n")
                    lines.append("</details>\n")
                elif cl_id in frameworks:
                    fw_item = frameworks[cl_id]
                    fw = fw_item["framework"]
                    rev = fw_item["review"]
                    lines.append("<details>")
                    lines.append(f"<summary><b>📖 Official Ebook Answer Framework</b></summary>\n")
                    lines.append(f"**1. Introduction:** {fw.get('suggested_introduction','')}\n")
                    lines.append(f"**2. Core Dimensions:**")
                    for dim in fw.get("core_dimensions", []):
                        lines.append(f"- {dim}")
                    lines.append(f"**3. Key Thinkers:** {', '.join(fw.get('key_thinkers_and_models', []))}\n")
                    lines.append(f"**4. Critical Evaluation:** {fw.get('critical_evaluation','')}\n")
                    lines.append(f"**5. Conclusion:** {fw.get('suggested_conclusion','')}\n")
                    lines.append("</details>\n")
                    
            lines.append("---\n")
            return lines

        md_lines.append("## Section I: Core Units\n")
        for a_id, u_data in sec1_core:
            md_lines.extend(format_unit_block(a_id, u_data))
            
        md_lines.append("## Section II: Core Units\n")
        for a_id, u_data in sec2_core:
            md_lines.extend(format_unit_block(a_id, u_data))
            
        md_lines.append("## Emergency Buffer Units\n")
        for a_id, u_data in buffers:
            md_lines.extend(format_unit_block(a_id, u_data))
            
        out_file = OUTPUT_DIR / f"{c_id}_study_pyq_bank.md"
        out_file.write_text("\n".join(md_lines), encoding="utf-8")
        print(f"Generated Markdown study bank with model answers: {out_file} ({len(md_lines)} lines)")

if __name__ == "__main__":
    generate_markdown_banks()
