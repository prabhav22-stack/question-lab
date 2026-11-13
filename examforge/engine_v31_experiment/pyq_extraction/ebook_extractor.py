import os
import sys
import re
from pathlib import Path
import pypdf

ROOT = Path("D:/Stuff/ExamForge")
EBOOK_BASE = ROOT / "MPA-1st Year"

COURSE_FOLDER_MAP = {
    "MPA-011": EBOOK_BASE / "MPA-011 State, Society and Public Administration",
    "MPA-012": EBOOK_BASE / "MPA-012 Administrative Theory",
    "MPA-013": EBOOK_BASE / "MPA-013 Public Systems Management",
    "MPA-014": EBOOK_BASE / "MPA-014 Human Resource Management",
}

def extract_unit_text(course_code, unit_numbers, max_chars=4000):
    """
    Extracts authentic syllabus text from the official IGNOU unit ebooks in MPA-1st Year.
    For combined units like MPA011-U01+U02, unit_numbers = [1, 2].
    """
    folder = COURSE_FOLDER_MAP.get(course_code)
    if not folder or not folder.exists():
        return ""
        
    combined_text = []
    
    for u_num in unit_numbers:
        pdf_file = folder / f"Unit-{u_num}.pdf"
        if not pdf_file.exists():
            # Try alternate naming
            alt = list(folder.glob(f"*Unit*{u_num}*.pdf"))
            if alt:
                pdf_file = alt[0]
                
        if pdf_file.exists():
            try:
                reader = pypdf.PdfReader(str(pdf_file))
                # Extract first 4-5 pages which contain Learning Outcome, Introduction, Concept Structure, Core Sections
                u_txt = []
                for p_idx in range(min(5, len(reader.pages))):
                    txt = reader.pages[p_idx].extract_text() or ""
                    u_txt.append(txt)
                full_u = "\n".join(u_txt)
                # Clean up excess whitespace
                clean_u = re.sub(r'\s+', ' ', full_u).strip()
                combined_text.append(f"--- [Official Ebook Unit {u_num}] ---\n{clean_u[:max_chars]}")
            except Exception as e:
                print(f"Error reading {pdf_file}: {e}")
                
    return "\n\n".join(combined_text)

if __name__ == "__main__":
    t = extract_unit_text("MPA-012", [4])
    print("Extracted length for MPA-012 Unit 4:", len(t))
    print(t[:250])
