# EXAMFORGE CANONICAL SYLLABUS REGISTRY: SOURCE VERIFICATION REPORT
## Academic Provenance, Digital Hashes and Primary Source Audit

**Audit Date:** November 11, 2026  
**Authority Source:** Official IGNOU Self-Learning Materials (SLM) & Course Textbooks  

### 1. Primary Academic Sources
The canonical syllabus registry derives its authority exclusively from official IGNOU academic textbooks and curriculum documents. Secondary sources (earlier AI summaries, legacy crosswalks, or unofficial web guides) are explicitly rejected as authoritative sources.

| Course Code | Official Textbook Document | File Size | Page Count | SHA-256 Checksum | Academic Authority |
| :--- | :--- | :---: | :---: | :--- | :---: |
| **MPA-011** | `MPA-011 State, Society and Public Administration.pdf` | 5,265,594 bytes | 344 pages | `5c7befd18ef8e610a96ca2846d4159d9c3f12e3d1065bd1f4b9f3e2a913fcbcf` | **Primary Authority** |
| **MPA-012** | `MPA-012 Administrative Theory.pdf` | 4,113,870 bytes | 394 pages | `c649b17d782fd1388836bd25d641be797a602198ad13adc3e581dfa2f804a65a` | **Primary Authority** |
| **MPA-013** | `MPA-013 Public Systems Management.pdf` | 6,089,315 bytes | 368 pages | `0451fff13861c455f95a2c2b7d744f301c07bdae22614a2cd571951d24eec9a9` | **Primary Authority** |
| **MPA-014** | `MPA-014 Human Resource Management.pdf` | 6,367,241 bytes | 440 pages | `f28bfef0aecd72999308cc11467b6d4a29bae4c20278b3d047097ab3cfa083b9` | **Primary Authority** |

---
### 2. Discrepancy Reconciliation & Historical Versioning
During the audit, discrepancies between physical booklet editions and eGyanKosh digital bundles were examined:

1. **MPA-014 Block Grouping Reconciliation:**
   - *Physical SLM Print Edition:* Published as 6 thematic blocks (Block 1: Intro; Block 2: Procurement; Block 3: Compensation; Block 4: Development; Block 5: Health & IR; Block 6: Emerging Trends).
   - *Online eGyanKosh Bundle:* Grouped units into 5 PDF bundles by combining Procurement and Compensation.
   - *Canonical Resolution:* The registry records the official 6-block thematic classification as authoritative, while registering the 5-bundle structure in `known_aliases.csv` for search compatibility.

2. **MPA-012 Unit Count Verification:**
   - *Legacy AI-Engine Flaw:* Earlier code frameworks assumed 24 units for MPA-012 by inserting dummy padding units.
   - *Official Course Book:* `MPA-012 Administrative Theory.pdf` contains exactly **22 units** (Unit 1 to Unit 22; pp. 1–394). The registry establishes 22 as the immutable canonical count.

3. **MPA-014 Unit Count Verification:**
   - *Legacy AI-Engine Flaw:* Earlier scripts assumed 24 units for MPA-014.
   - *Official Course Book:* `MPA-014 Human Resource Management.pdf` contains exactly **23 units** (Unit 1 to Unit 23; pp. 1–440). Unit 23 (*Stress Management*) is the final unit.
