import os
import sys
import csv
import json
import html
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

ROOT = Path("D:/Stuff/ExamForge")
OUTPUT_DIR = ROOT / "engine_v31_experiment/pyq_extraction/outputs"
PDF_DIR = OUTPUT_DIR / "pdf"
PDF_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = OUTPUT_DIR / "locked_units_clustered_pyqs.csv"
MODEL_ANSWERS_PATH = OUTPUT_DIR / "model_answers.json"

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            return  # Skip cover page
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4A5568"))
        
        # Header (Top)
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(36, 806, 559, 806)
        doc_title = getattr(self, "doc_title", "IGNOU MPA PYQ Study Bank & Model Answers — Dec 2026")
        self.drawString(36, 810, doc_title)
        self.drawRightString(559, 810, "ExamForge v3.1 Engine")
        
        # Footer (Bottom)
        self.line(36, 45, 559, 45)
        self.drawString(36, 32, "GROUNDED IN OFFICIAL IGNOU EBOOKS (`MPA-1st Year`) | VERIFIED MODEL ANSWERS")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(559, 32, page_str)
        self.restoreState()

def get_reportlab_styles():
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1A365D'),
        alignment=1,
        spaceAfter=8
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#4A5568'),
        alignment=1,
        spaceAfter=14
    )
    
    h1_style = ParagraphStyle(
        'HeaderH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#1A365D'),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    cluster_title_style = ParagraphStyle(
        'ClusterTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#1A202C'),
        keepWithNext=True
    )

    meta_badge_style = ParagraphStyle(
        'MetaBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor('#2C5282'),
        alignment=2
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#2D3748')
    )

    q_text_style = ParagraphStyle(
        'QText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor('#1A202C')
    )

    ma_box_style = ParagraphStyle(
        'MaBox',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=11,
        textColor=colors.HexColor('#1A202C')
    )

    cell_style = ParagraphStyle(
        'TdStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#2D3748')
    )

    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "h1": h1_style,
        "cluster_title": cluster_title_style,
        "badge": meta_badge_style,
        "body": body_style,
        "q_text": q_text_style,
        "ma_box": ma_box_style,
        "td": cell_style
    }

def esc(text):
    return html.escape(str(text)) if text else ""

def render_study_bank_story(c_id, course_data, model_answers, is_combined=False):
    styles = get_reportlab_styles()
    story = []
    
    course_info = {
        "MPA-011": ("State, Society and Public Administration", "Wednesday, Dec 2, 2026", "5-Year Beta-Binomial (Full 20M Essay Mode)"),
        "MPA-012": ("Administrative Theory", "Thursday, Dec 3, 2026", "15-Year No-Cooldown (Classical Split Q5 & Q10: 10+10)"),
        "MPA-013": ("Public Systems Management", "Friday, Dec 4, 2026", "15-Year Unweighted Stabilized Memory (Retains Unit 25 in Core)"),
        "MPA-014": ("Human Resource Management", "Saturday, Dec 5, 2026", "5-Year Beta-Binomial (Worker Participation Surge)")
    }
    
    c_title, c_date, c_model = course_info[c_id]
    u_dict = course_data[c_id]
    
    if not is_combined:
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"IGNOU MA PUBLIC ADMINISTRATION (1st Year)", styles["subtitle"]))
        story.append(Paragraph(f"{c_id}: {c_title.upper()}", styles["title"]))
        story.append(Paragraph(f"<b>December 2026 Term-End Examination High-Frequency PYQ Study Bank & Model Answers</b><br/>Official IGNOU Ebook Grounded & AI-Verified Full-Length Essay Answers", styles["subtitle"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1A365D"), spaceAfter=10))

        meta_table = [
            [
                Paragraph(f"<b>Exam Date:</b> {c_date}<br/><b>Format Architecture:</b> {c_model}", styles["td"]),
                Paragraph(f"<b>Model Answers:</b> Full 500w Essay / 250w Note Depth<br/><b>Memory Window:</b> 11 Sessions (Jun 2021–Jun 2026)", styles["td"]),
                Paragraph(f"<b>Source Ebooks:</b> Official IGNOU `MPA-1st Year`<br/><b>Verification:</b> Groq Academic Quality Control", styles["td"])
            ]
        ]
        t_meta = Table(meta_table, colWidths=[170, 175, 178])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F7FAFC')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 12))
    else:
        story.append(Paragraph(f"{c_id}: {c_title.upper()}", styles["h1"]))
        story.append(Paragraph(f"<b>Exam Date:</b> {c_date} | <b>Architecture:</b> {c_model}", styles["body"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=8))

    sec1_core = [item for item in u_dict.items() if item[1]["portfolio_tier"] == "10_CORE" and item[1]["section"] == "Section I"]
    sec2_core = [item for item in u_dict.items() if item[1]["portfolio_tier"] == "10_CORE" and item[1]["section"] == "Section II"]
    buffers = [item for item in u_dict.items() if item[1]["portfolio_tier"] != "10_CORE"]

    def render_unit_elements(a_id, u_data):
        elements = []
        tier_label = "CORE 10 (Full 500-Word Essay Preparation)" if u_data["portfolio_tier"] == "10_CORE" else "EMERGENCY BUFFER (250-Word Targeted Skeleton)"
        tier_color = "#22543D" if u_data["portfolio_tier"] == "10_CORE" else "#744210"
        
        header_text = f"<b>Unit {esc(a_id)}: {esc(u_data['unit_title'])}</b><br/><font color='{tier_color}'><b>{tier_label}</b></font> | <b>Section:</b> {esc(u_data['section'])}"
        u_box = Table([[Paragraph(header_text, styles["body"])]], colWidths=[523])
        u_box.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EDF2F7')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(u_box)
        elements.append(Spacer(1, 6))

        sorted_clusters = sorted(u_data["clusters"].values(), key=lambda x: x["cluster_rank"])
        top_n = 5 if u_data["portfolio_tier"] == "10_CORE" else 2
        selected_clusters = sorted_clusters[:top_n]

        for c in selected_clusters:
            cl_id = c["cluster_id"]
            tma_badge_str = " | 🎯 TMA CONFIRMED" if c["tma_match"] == "YES" else ""
            cl_head = f"<b>Rank {c['cluster_rank']} | {esc(c['cluster_title'])}{tma_badge_str}</b>"
            badge = f"<b>[5-Yr: {c['freq_5yr']}/{c['available_sessions_5yr']} | All: {c['freq_all']} | TMA: {c['tma_match']}]</b>"

            tma_line = (f"• <b>🎯 TMA Signal:</b> {esc(c['tma_evidence'])}"
                        if c["tma_match"] == "YES"
                        else "• <b>TMA Status:</b> No direct TMA overlap detected")
            cl_table_data = [
                [Paragraph(cl_head, styles["cluster_title"]), Paragraph(badge, styles["badge"])],
                [
                    Paragraph(
                        f"• <b>5-Yr Sessions:</b> {c['freq_5yr']} ({c['occurrences_5yr']} appearances) | <b>All-Time:</b> {c['freq_all']} occurrences across {c['sessions_all']} sessions<br/>"
                        f"• <b>Last Asked:</b> {esc(c['last_asked'])} | <b>Format:</b> FULL_20M: {c['full_20m_count']}, SPLIT_10M: {c['split_10m_count']}<br/>"
                        f"{tma_line}",
                        styles["td"]
                    ),
                    ""
                ]
            ]
            t_cl = Table(cl_table_data, colWidths=[370, 153])
            t_cl.setStyle(TableStyle([
                ('SPAN', (0,1), (1,1)),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F7FAFC' if c["tma_match"] != "YES" else '#F0FFF4')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0' if c["tma_match"] != "YES" else '#9AE6B4')),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ('LEFTPADDING', (0,0), (-1,-1), 5),
                ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ]))
            elements.append(t_cl)
            elements.append(Spacer(1, 4))

            # Verbatim Historical Questions (Top 3 Representative)
            q_elements = []
            sample_qs = c["questions"][:3]
            for q in sample_qs:
                tag = f"<b>[{esc(q['session'])} | Q{esc(q['question_number'])}{esc(q['subquestion'])} | {esc(q['section'])} | {esc(q['format_type'])} | {esc(q['marks'])}M]</b>"
                q_p = Paragraph(f"{tag} {esc(q['question_text'])}", styles["q_text"])
                q_elements.append([q_p])
                
            t_q = Table(q_elements, colWidths=[523])
            t_q.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.white),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
                ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#EDF2F7')),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ]))
            elements.append(t_q)
            elements.append(Spacer(1, 4))

            # FULL-LENGTH MODEL ANSWER (Rank 1 primary)
            if c['cluster_rank'] == 1 and cl_id in model_answers:
                ma = model_answers[cl_id]
                sdata = ma.get("structured_data", {})
                
                intro = sdata.get("introduction", "")
                body_secs = sdata.get("body_sections", [])
                eval_sec = sdata.get("critical_evaluation", "")
                concl_sec = sdata.get("conclusion", "")
                thinkers = ", ".join(esc(t) for t in sdata.get("key_thinkers_cited", []))
                
                body_formatted = []
                for b in body_secs:
                    body_formatted.append(f"<b><u>{esc(b.get('heading',''))}</u></b><br/>{esc(b.get('content',''))}")
                body_str = "<br/><br/>".join(body_formatted)
                
                ma_content = (
                    f"<font color='#1A365D'><b>📝 OFFICIAL FULL-LENGTH MODEL ANSWER ({esc(ma.get('format'))} | {esc(ma.get('marks'))} Marks | {esc(ma.get('word_count_target'))})</b></font><br/>"
                    f"<i>Question: \"{esc(ma.get('representative_question'))}\"</i><br/>"
                    f"<i>Grounded in official IGNOU study materials from `MPA-1st Year` | Verified via Groq</i><br/><br/>"
                    f"<b><u>Introduction:</u></b><br/>{esc(intro)}<br/><br/>"
                    f"{body_str}<br/><br/>"
                    f"<b><u>Critical Evaluation & Administrative Relevance:</u></b><br/>{esc(eval_sec)}<br/><br/>"
                    f"<b><u>Conclusion:</u></b><br/>{esc(concl_sec)}<br/><br/>"
                    f"<b>Core Thinkers / Concepts:</b> {thinkers}"
                )
                
                t_ma = Table([[Paragraph(ma_content, styles["ma_box"])]], colWidths=[523])
                t_ma.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0FFF4')),
                    ('BOX', (0,0), (-1,-1), 0.75, colors.HexColor('#38A169')),
                    ('TOPPADDING', (0,0), (-1,-1), 6),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ('LEFTPADDING', (0,0), (-1,-1), 8),
                    ('RIGHTPADDING', (0,0), (-1,-1), 8),
                ]))
                elements.append(t_ma)
                elements.append(Spacer(1, 8))

        elements.append(Spacer(1, 6))
        return elements

    story.append(Paragraph("Section I: Core Units", styles["h1"]))
    for a_id, u_data in sec1_core:
        story.extend(render_unit_elements(a_id, u_data))

    story.append(Paragraph("Section II: Core Units", styles["h1"]))
    for a_id, u_data in sec2_core:
        story.extend(render_unit_elements(a_id, u_data))

    story.append(Paragraph("Emergency Buffer Units", styles["h1"]))
    for a_id, u_data in buffers:
        story.extend(render_unit_elements(a_id, u_data))

    return story

def build_all_pdfs():
    print("Building all 4 individual course PDFs and 1 consolidated master PDF with Full Model Answers...")
    
    with open(CSV_PATH, encoding="utf-8") as f:
        records = list(csv.DictReader(f))
        
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
        
    for c_id in ["MPA-011", "MPA-012", "MPA-013", "MPA-014"]:
        out_pdf = PDF_DIR / f"{c_id}_LOCKED_PYQ_STUDY_BANK_DEC_2026.pdf"
        doc = SimpleDocTemplate(
            str(out_pdf),
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=46,
            bottomMargin=54
        )
        story = render_study_bank_story(c_id, course_data, model_answers, is_combined=False)
        doc.build(story, canvasmaker=NumberedCanvas)
        print(f"Generated individual PDF with model answers: {out_pdf}")

    master_pdf = PDF_DIR / "FINAL_COMBINED_LOCKED_PYQ_STUDY_BANK_DEC_2026.pdf"
    master_doc = SimpleDocTemplate(
        str(master_pdf),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=54
    )
    styles = get_reportlab_styles()
    master_story = []
    
    master_story.append(Spacer(1, 25))
    master_story.append(Paragraph("EXAMFORGE ENGINE v3.1 PRODUCTION", styles["title"]))
    master_story.append(Paragraph("MASTER COMBINED HISTORICAL PYQ STUDY BANK & COMPLETE MODEL ANSWERS<br/><b>IGNOU MA Public Administration (MPA 1st Year) — December 2026 TEE</b>", styles["subtitle"]))
    master_story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1A365D"), spaceAfter=14))

    master_meta = [
        [
            Paragraph("<b>Target Examination Timetable</b><br/>• MPA-011: Wed, Dec 2, 2026<br/>• MPA-012: Thu, Dec 3, 2026<br/>• MPA-013: Fri, Dec 4, 2026<br/>• MPA-014: Sat, Dec 5, 2026", styles["td"]),
            Paragraph("<b>Full Model Answers Included</b><br/>• 48 Full Model Answers (500w / 250w)<br/>• Grounded in `MPA-1st Year` Unit text<br/>• Introduction, Core, Evaluation & Concl.", styles["td"]),
            Paragraph("<b>Authoritative Source Grounding</b><br/>• Official IGNOU Ebooks (`MPA-1st Year`)<br/>• 31 Examination Sessions (2011–2026)<br/>• Verified TMA Signals (2025–2027)<br/>• Groq AI Factual Review Verification", styles["td"])
        ]
    ]
    t_m = Table(master_meta, colWidths=[170, 175, 178])
    t_m.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F7FAFC')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    master_story.append(t_m)
    master_story.append(Spacer(1, 20))

    for idx, c_id in enumerate(["MPA-011", "MPA-012", "MPA-013", "MPA-014"]):
        master_story.append(PageBreak())
        c_story = render_study_bank_story(c_id, course_data, model_answers, is_combined=True)
        master_story.extend(c_story)

    master_doc.build(master_story, canvasmaker=NumberedCanvas)
    print(f"Generated consolidated master PDF with model answers: {master_pdf}")

if __name__ == "__main__":
    build_all_pdfs()
