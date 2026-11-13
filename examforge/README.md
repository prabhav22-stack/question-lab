# ExamForge v3.1: Public Administration & MPA Laboratory

ExamForge is an integrated examination intelligence and study forecasting engine tailored for Civil Services Public Administration (UPSC & BPSC Optional) and IGNOU Master of Public Administration (MPA First-Year).

---

## 🌟 Key Capabilities

1. **15-Year Historical PYQ Archive (2011–2026):**
   - **951 authentic past examination questions** mapped across 31 historical sessions.
   - Normalized and marks-verified with format attribution (`FULL_20M`, `SPLIT_10M`).

2. **Semantic Clustering (TF-IDF + AI Verified):**
   - **234 distinct thematic clusters** ranked by 5-year recency and historical occurrence frequency.
   - Eliminates redundant preparation by grouping verbatim question variations under core conceptual themes.

3. **Tutor Marked Assignment (TMA) Signal Detection:**
   - Conceptually cross-mapped against official TMA assignments for the 2025–26 and 2026–27 cycles.
   - Direct indicator badges highlighting units and themes with active assignment overlap.

4. **100% Ebook-Grounded Model Essay Answers:**
   - **48 comprehensive, structured 500-word model answers** grounded directly in official textbooks.
   - Complete analytical framework: Introduction, Detailed Thematic Body Sections, Critical Evaluation & Contemporary Administrative Relevance, Conclusion, and Thinker/Theorist Citations (Taylor, Fayol, Weber, Simon, Waldo, Riggs, etc.).

5. **Courses Covered:**
   - **MPA-011:** State, Society and Public Administration
   - **MPA-012:** Administrative Theory
   - **MPA-013:** Public Systems Management
   - **MPA-014:** Human Resource Management

---

## 🚀 How to Run

### Option 1: Inside Question Lab (Unified UI)
In Question Lab, select **`🎓 ExamForge: MPA Lab`** from the sidebar navigation.

### Option 2: Standalone Mode
Run the standalone ExamForge portal:
```powershell
.\.venv\Scripts\python.exe -m streamlit run examforge/app.py
```

---

## 📑 Included Study Assets

- **Consolidated Master Study Bank PDF (73 Pages)**: `engine_v31_experiment/pyq_extraction/outputs/pdf/FINAL_COMBINED_LOCKED_PYQ_STUDY_BANK_DEC_2026.pdf`
- **Course PDFs**: Individual PDFs for MPA-011, MPA-012, MPA-013, and MPA-014.
- **NotebookLM Markdown Banks**: Ready for direct upload to Google NotebookLM.
- **Executive Prioritised Units Guide PDF**: `DEC_2026_PRIORITISED_UNITS_AND_SUBTOPICS_GUIDE.pdf`
