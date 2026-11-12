"""Shared read-only Excel roster parser for grade sheets (ม.1–ม.6)."""
import datetime
import re
from typing import Any, Dict, Iterator, List, Optional, Tuple

GRADE_SHEETS = ["ม.1", "ม.2", "ม.3", "ม.4", "ม.5", "ม.6"]
PREFIXES = ["เด็กชาย", "เด็กหญิง", "นางสาว", "นาย", "นาง", "ด.ช.", "ด.ญ."]
MALE_PREFIXES = {"เด็กชาย", "นาย", "ด.ช."}
FEMALE_PREFIXES = {"เด็กหญิง", "นางสาว", "นาง", "ด.ญ."}

TITLE_RE = re.compile(r"ชั้นมัธยมศึกษาปีที่\s*(\d+)\s*/\s*(\d+)")
YEAR_RE = re.compile(r"ปีการศึกษา\s*(\d{4})")
SEM_RE = re.compile(r"ภาคเรียนที่\s*(\d+)")


def clean(s):
    if s is None:
        return None
    if isinstance(s, str):
        s = s.replace("\xa0", " ").strip()
        return s if s else None
    return s


def split_name(raw_name):
    name = clean(raw_name)
    if not name:
        return None, None, None, None, None
    prefix, rest = None, name
    for p in sorted(PREFIXES, key=len, reverse=True):
        if name.startswith(p):
            prefix, rest = p, name[len(p):].strip()
            break
    parts = rest.split()
    first_name = parts[0] if parts else None
    last_name = " ".join(parts[1:]) if len(parts) > 1 else None
    gender = "M" if prefix in MALE_PREFIXES else ("F" if prefix in FEMALE_PREFIXES else None)
    return prefix, first_name, last_name, name, gender


def _format_ymd(y: int, m: int, d: int, fallback: Optional[str] = None) -> Optional[str]:
    if y > 2400:
        y -= 543
    try:
        return datetime.date(y, m, d).isoformat()
    except ValueError:
        return fallback if fallback is not None else f"{y:04d}-{m:02d}-{d:02d}"


def normalize_date(val):
    if val is None:
        return None
    if isinstance(val, datetime.datetime):
        return _format_ymd(val.year, val.month, val.day)
    s = clean(val)
    if not s:
        return None
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m:
        return _format_ymd(int(m.group(3)), int(m.group(2)), int(m.group(1)), fallback=s)
    return s


def to_int(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    s = clean(val)
    return int(s) if s and s.isdigit() else None


def col(row: Tuple[Any, ...], idx: int) -> Any:
    return row[idx] if len(row) > idx else None


def _parse_header_meta(header: str) -> Optional[Tuple[int, int, Optional[int], Optional[int], Optional[str]]]:
    title_match = TITLE_RE.search(header)
    if not title_match:
        return None
    grade, room = int(title_match.group(1)), int(title_match.group(2))
    ym, sm = YEAR_RE.search(header), SEM_RE.search(header)
    year = int(ym.group(1)) if ym else None
    if year and year > 2400:
        year -= 543
    semester = int(sm.group(1)) if sm else None
    track = SEM_RE.sub("", YEAR_RE.sub("", TITLE_RE.sub("", header)))
    track = clean(track.replace("ภาคเรียนที่", "")) or None
    return grade, room, year, semester, track


def _build_grade_row(a, b, c, d, meta) -> Optional[Dict[str, Any]]:
    student_id = to_int(b)
    if not student_id:
        return None
    grade, room, year, semester, track = meta
    prefix, first, last, full, gender = split_name(c)
    return {
        "student_id": student_id,
        "national_id": clean(str(d)) if d is not None else None,
        "prefix": prefix, "first_name": first, "last_name": last,
        "full_name": full, "gender": gender,
        "grade_level": f"ม.{grade}" if grade else None,
        "room": room, "track": track, "seq_no": to_int(a),
        "academic_year": year, "semester": semester,
    }


def iter_grade_rows(ws) -> Iterator[Dict[str, Any]]:
    meta = (None, None, None, None, None)
    in_block = False
    for row in ws.iter_rows(values_only=True):
        a, b, c, d = clean(col(row, 0)), col(row, 1), clean(col(row, 2)), col(row, 3)
        parsed_meta = _parse_header_meta(str(a)) if a else None
        if parsed_meta:
            meta, in_block = parsed_meta, False
            continue
        if a == "ที่":
            in_block = True
            continue
        if in_block and isinstance(b, (int, float)) and c:
            item = _build_grade_row(a, b, c, d, meta)
            if item:
                yield item
        elif in_block and a is None and b is None:
            in_block = False


def parse_grade_workbook(file_path: str) -> List[Dict[str, Any]]:
    import openpyxl

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    rows: List[Dict[str, Any]] = []
    try:
        for name in wb.sheetnames:
            if name in GRADE_SHEETS:
                rows.extend(iter_grade_rows(wb[name]))
    finally:
        wb.close()
    return rows
