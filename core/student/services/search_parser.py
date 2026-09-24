import re
from typing import Optional, Tuple

GRADE_WITH_PREFIX_RE = re.compile(r"^ม\.?(\d)(?:[./](\d+))?$")
GRADE_NO_PREFIX_RE = re.compile(r"^(\d)[./](\d+)$")


def clean_query(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def parse_grade_room(query: str) -> Optional[Tuple[str, Optional[int]]]:
    clean = clean_query(query)
    m = GRADE_WITH_PREFIX_RE.match(clean) or GRADE_NO_PREFIX_RE.match(clean)
    if not m:
        return None
    grade, room = m.groups()
    return f"ม.{grade}", int(room) if room else None
