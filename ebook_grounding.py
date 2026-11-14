"""Official IGNOU MPA Ebook Content Extractor for Grounding AI Tutor."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

try:
    import pymupdf  # type: ignore
except ImportError:
    try:
        import fitz as pymupdf  # type: ignore
    except ImportError:
        pymupdf = None

BASE_DIR = Path(__file__).parent.resolve()
EBOOK_DIRS = [
    BASE_DIR / "examforge" / "MPA-1st Year",
    Path("D:/Stuff/ExamForge/MPA-1st Year"),
]


def _get_ebook_root() -> Optional[Path]:
    for p in EBOOK_DIRS:
        if p.exists() and p.is_dir():
            return p
    return None


def extract_unit_ebook_content(course_id: str, unit_id: str, max_chars: int = 8000) -> str:
    """Extract authentic text from the official IGNOU unit ebook PDF.
    
    Args:
        course_id: e.g. 'MPA-011'
        unit_id: e.g. 'MPA011-U04' or 'MPA011-U01+U02'
        max_chars: Maximum characters to include for grounding
    """
    if pymupdf is None:
        return ""

    root = _get_ebook_root()
    if not root:
        return ""

    # Normalize course code e.g. MPA-011 -> MPA011
    c_norm = course_id.replace("-", "").upper()
    course_dirs = [d for d in root.iterdir() if d.is_dir() and c_norm in d.name.replace("-", "").upper()]
    if not course_dirs:
        return ""
    course_dir = course_dirs[0]

    # Extract unit number(s) from analytical_unit_id: 'MPA011-U04' -> [4], 'MPA011-U01+U02' -> [1, 2]
    u_nums = [int(n) for n in re.findall(r"U0?(\d+)", unit_id, re.IGNORECASE)]
    if not u_nums:
        m = re.findall(r"(\d+)", unit_id)
        if m:
            u_nums = [int(m[-1])]

    extracted_sections: List[str] = []
    budget_per_unit = max_chars // max(1, len(u_nums))

    for u in u_nums:
        target_file = course_dir / f"Unit-{u}.pdf"
        if not target_file.exists():
            matches = list(course_dir.glob(f"*Unit*{u}*.pdf"))
            if matches:
                target_file = matches[0]

        if target_file.exists():
            try:
                doc = pymupdf.open(str(target_file))
                unit_text: List[str] = []
                # Extract all pages up to budget
                total_len = 0
                for page in doc:
                    txt = page.get_text("text") or ""
                    cleaned = re.sub(r"[ \t]+", " ", txt).strip()
                    if cleaned:
                        unit_text.append(cleaned)
                        total_len += len(cleaned)
                        if total_len >= budget_per_unit:
                            break
                full_text = "\n\n".join(unit_text)
                extracted_sections.append(
                    f"--- [OFFICIAL IGNOU EBOOK: {course_id} UNIT {u}] ---\n"
                    f"{full_text[:budget_per_unit]}"
                )
            except Exception:
                pass

    return "\n\n".join(extracted_sections)
