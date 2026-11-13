"""
ExamForge Engine v3.1 - PDF Generator:
Combined Unit Priorities & Subtopic Compendium for December 2026 TEE
(MPA-011, MPA-012, MPA-013, MPA-014)
"""

import sys
import os
import pandas as pd

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

# Canvas for Page Numbers and Running Header
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
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#4B5563"))
        
        # Header (Only on page 2 onwards)
        if self._pageNumber > 1:
            self.drawString(54, 750, "EXAMFORGE ENGINE v3.1 — UNIT PRIORITIES & SUBTOPIC BLUEPRINT (DECEMBER 2026 TEE)")
            self.drawRightString(558, 750, "CONFIDENTIAL STUDY GUIDE")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)

        # Footer
        self.setFont("Helvetica", 8)
        self.drawString(54, 36, "IGNOU MA Public Administration (MPA 1st Year) | 10 Core Units + 2 Buffer Subtopics")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_text)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 48, 558, 48)
        self.restoreState()

def build_pdf():
    pdf_filename = "outputs/IGNOU_MPA_1st_Year_Dec2026_Unit_Priorities_Compendium.pdf"
    os.makedirs(os.path.dirname(pdf_filename), exist_ok=True)
    
    # Also replicate in engine_v31_experiment/outputs
    exp_pdf = "engine_v31_experiment/outputs/IGNOU_MPA_1st_Year_Dec2026_Unit_Priorities_Compendium.pdf"
    
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=1, # Center
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#0D9488'),
        alignment=1,
        spaceAfter=14
    )
    
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#374151'),
        alignment=1,
        spaceAfter=18
    )
    
    course_header_style = ParagraphStyle(
        'CourseHeader',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=10,
        spaceAfter=6
    )
    
    sec_header_style = ParagraphStyle(
        'SecHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0F766E'),
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'TableBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1F2937')
    )

    body_bold = ParagraphStyle(
        'TableBodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#111827')
    )

    subtopic_style = ParagraphStyle(
        'SubtopicText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#4B5563')
    )

    badge_core = ParagraphStyle(
        'BadgeCore',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor('#1E40AF'),
        alignment=1
    )

    badge_buffer = ParagraphStyle(
        'BadgeBuffer',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor('#9A3412'),
        alignment=1
    )

    # Load frozen portfolio
    frozen_df = pd.read_csv('engine_v31_experiment/outputs/december_2026_frozen_portfolio.csv')
    
    # Load canonical topics
    topic_df = pd.read_csv('shared/canonical_syllabus_registry/topic_registry.csv')
    
    elements = []
    
    # Cover / Header Section
    elements.append(Paragraph("EXAMFORGE ENGINE v3.1", title_style))
    elements.append(Paragraph("DECEMBER 2026 TERM-END EXAMINATION — MASTER UNIT PRIORITIES & SUBTOPICS", subtitle_style))
    elements.append(Paragraph(
        "<b>Rigorous 10 Core Units + 2 Emergency Buffer Subtopics Compendium</b><br/>"
        "Derived via Chronological Walk-Forward Optimization (2021–2026), Section Parity Modeling & Current Cycle TMA Signal<br/>"
        "<b>Examination Timetable:</b> MPA-011 (Dec 2) &bull; MPA-012 (Dec 3) &bull; MPA-013 (Dec 4) &bull; MPA-014 (Dec 5, 2026) | 2:00 PM – 5:00 PM",
        meta_style
    ))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceAfter=14))
    
    # Strategic Architecture Alert
    alert_text = (
        "<b>OPERATIONAL ARCHITECTURE (10 CORE + 2 BUFFER SUBTOPICS):</b><br/>"
        "&bull; <b>Statutory Rule:</b> Answer exactly 5 questions out of 10, selecting at least 2 from Section I and at least 2 from Section II.<br/>"
        "&bull; <b>10 Core Units:</b> Prepared in full 500-word essay depth (5 in Section I, 5 in Section II) guaranteeing 100% legal question coverage.<br/>"
        "&bull; <b>2 Buffer Subtopics:</b> Specific 250-word targeted skeletons (1 for Sec I, 1 for Sec II) providing emergency 10M salvage protection without bloating study volume between consecutive exam afternoons."
    )
    alert_table = Table([[Paragraph(alert_text, body_style)]], colWidths=[504])
    alert_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0FDF4')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#16A34A')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(alert_table)
    elements.append(Spacer(1, 14))

    courses_meta = [
        ('MPA-011', 'State, Society and Public Administration', 'Wednesday, Dec 2, 2026', 'Full 20M Essay Mode (Zero Short-Note Trap)'),
        ('MPA-012', 'Administrative Theory', 'Thursday, Dec 3, 2026', 'Classical Split Model (Q5 & Q10: 10+10 Short Notes)'),
        ('MPA-013', 'Public Systems Management', 'Friday, Dec 4, 2026', '15-Year Stabilized Memory (Q5 & Q10: 10+10 Short Notes)'),
        ('MPA-014', 'Human Resource Management', 'Saturday, Dec 5, 2026', 'Full 20M Essay Mode (Worker Participation Surge)')
    ]

    for idx, (code, title, exam_date, paper_mode) in enumerate(courses_meta):
        if idx > 0:
            elements.append(PageBreak())
            
        c_df = frozen_df[frozen_df['course_code'] == code]
        
        # Course Header Box
        header_html = f"<b>{code}: {title.upper()}</b><br/><font size=8 color='#4B5563'><b>Date:</b> {exam_date} &bull; <b>Format Model:</b> {paper_mode}</font>"
        elements.append(Paragraph(header_html, course_header_style))
        elements.append(Spacer(1, 4))
        
        # Table of Units
        # Columns: Role, Section, Unit, Official Title, Priority Score, High-Yield Subtopics & Canonical Syllabus Breakdown
        col_widths = [62, 50, 48, 140, 204]
        
        table_data = [[
            Paragraph("<b>Role</b>", body_bold),
            Paragraph("<b>Section</b>", body_bold),
            Paragraph("<b>Unit ID</b>", body_bold),
            Paragraph("<b>Official Unit Title</b>", body_bold),
            Paragraph("<b>High-Yield Focus & Detailed Subtopics</b>", body_bold)
        ]]
        
        # Sort so Section I Core, Section I Buffer, Section II Core, Section II Buffer are grouped
        c_df_sorted = c_df.sort_values(by=['section', 'role', 'unit_number'], ascending=[True, True, True])
        
        for _, r in c_df_sorted.iterrows():
            role = r['role']
            sec = r['section']
            u_num = r['unit_number']
            can_id = r['canonical_unit_id']
            u_title = r['official_unit_title']
            score = r['forecast_score']
            tma_sub = r['high_yield_subtopic_focus']
            
            # Fetch canonical substantive topics from topic_df
            u_topics = topic_df[topic_df['canonical_unit_id'] == can_id]
            filtered_topics = u_topics[~u_topics['official_topic_title'].str.contains(
                'Introduction|Conclusion|Learning Outcome|References|Activities|Key Concepts|A ctivities', 
                case=False, na=False
            )]['official_topic_title'].tolist()
            
            topics_snippet = " &bull; ".join(filtered_topics[:4]) if filtered_topics else "Complete Chapter Preparation"
            
            if role == '10_CORE':
                role_p = Paragraph("<font color='#1E40AF'><b>10 CORE</b></font><br/><font size=6.5 color='#6B7280'>Score: " + f"{score:.2f}" + "</font>", badge_core)
            else:
                role_p = Paragraph("<font color='#C2410C'><b>BUFFER</b></font><br/><font size=6.5 color='#6B7280'>250w Skeleton</font>", badge_buffer)
                
            sec_p = Paragraph(f"<b>{sec}</b>", body_style)
            unit_p = Paragraph(f"<b>Unit {u_num:02d}</b><br/><font size=6.5 color='#6B7280'>{can_id}</font>", body_bold)
            title_p = Paragraph(f"<b>{u_title}</b>", body_style)
            
            subtopic_html = (
                f"<b>High-Yield TEE / TMA Target:</b><br/>"
                f"<font color='#0F766E'>&bull; {tma_sub}</font><br/>"
                f"<font color='#374151'><b>Syllabus Sub-Themes:</b> {topics_snippet}</font>"
            )
            sub_p = Paragraph(subtopic_html, subtopic_style)
            
            table_data.append([role_p, sec_p, unit_p, title_p, sub_p])
            
        unit_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Table Styling
        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]
        
        # Alternating row colors
        for r_idx in range(1, len(table_data)):
            if r_idx % 2 == 0:
                t_style.append(('BACKGROUND', (0, r_idx), (-1, r_idx), colors.HexColor('#F8FAFC')))
                
        unit_table.setStyle(TableStyle(t_style))
        elements.append(unit_table)
        elements.append(Spacer(1, 10))
        
        # Subject Specific Strategy Box
        strat_notes = {
            'MPA-011': "<b>Exam Hall Execution Tip:</b> MPA-011 in Dec 2025 and June 2026 omitted short-note subparts. Write full 500-word structured essays for all 5 questions. Unit 2 (State-Society / Riggs) and Unit 12 (Bureaucracy) have appeared consecutively in 100% of recent papers.",
            'MPA-012': "<b>Exam Hall Execution Tip:</b> Expect Q5 and Q10 to be split into 10+10 mark notes. Elton Mayo (U8) and Motivation (U12/U13) are immortal anchors. For Herbert Simon (U9) and Edgar Schein (U17), ensure clear conceptual diagrams.",
            'MPA-013': "<b>Exam Hall Execution Tip:</b> Grounded in 15-year historical memory to resist wide multi-block drift. Master Unit 19 (Accountability) and Unit 23 (Reforms & Change Management) to secure Section II.",
            'MPA-014': "<b>Exam Hall Execution Tip:</b> Section II is dominated by Industrial Relations. Unit 17 (Workers' Participation & Quality Circles) and Unit 18 (Collective Bargaining) provide high-scoring clarity."
        }
        strat_box = Table([[Paragraph(strat_notes[code], body_style)]], colWidths=[504])
        strat_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EFF6FF')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#3B82F6')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(strat_box)

    doc.build(elements, canvasmaker=NumberedCanvas)
    
    # Copy to experiment output directory
    import shutil
    shutil.copy2(pdf_filename, exp_pdf)
    print(f"Generated successfully: {pdf_filename} and {exp_pdf}")

if __name__ == '__main__':
    build_pdf()
