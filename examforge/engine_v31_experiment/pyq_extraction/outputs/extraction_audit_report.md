# ExamForge v3.1: PYQ Extraction, Clustering & Ranking Audit Report
**Date:** November 12, 2026 | **Execution Mode:** Reproducible Pipeline with Groq AI Verification

## 1. Extraction Volume & Portfolio Statistics
- **Total Extracted Question Records:** 951
- **Total Distinct Semantic Clusters:** 234
- **Distinct Historical Sessions Covered:** 31 (2011–2026)

### Breakdown by Course:
| Course Code | Extracted PYQs | Distinct Clusters | Core Units | Buffer Units |
|---|---:|---:|---:|---:|
| **MPA-011** | 258 | 51 | 10 | 2 |
| **MPA-012** | 257 | 59 | 10 | 2 |
| **MPA-013** | 220 | 75 | 10 | 2 |
| **MPA-014** | 216 | 49 | 11 | 1 |

## 2. Portfolio Adjustments Executed
1. **MPA-011:** Combined `MPA011-U01` (Nature of the State) and `MPA011-U02` (Relationship between State, Society and Public Administration) into single analytical unit `MPA011-U01+U02` without deleting underlying canonical IDs.
2. **MPA-014:** Promoted `MPA014-U06` (Performance Appraisal) from Buffer to Full Core (Total Core: 11 units).

## 3. Question Formats & Marks Breakdown
- **FULL_20M:** 794 questions
- **SPLIT_10M:** 157 questions
- **Unknown / Other:** 0 questions

## 4. Source Traceability
- **Official IGNOU Ebooks:** Loaded from `D:\Stuff\ExamForge\MPA-1st Year` (All 91 unit PDFs verified).
- **Groq Verification Models:** Primary: `openai/gpt-oss-120b`, Reviewer: `openai/gpt-oss-20b`.