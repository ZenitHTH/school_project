from dataclasses import dataclass
from typing import Optional, Set, Tuple


@dataclass
class Student:
    student_id: int
    national_id: Optional[str]
    prefix: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: str
    gender: Optional[str]
    status: str
    grade_level: Optional[str] = None
    room: Optional[int] = None
    track: Optional[str] = None
    academic_year: Optional[int] = None
    semester: Optional[int] = None


@dataclass
class Enrollment:
    id: int
    student_id: int
    academic_year: int
    semester: int
    grade_level: str
    room: int
    track: Optional[str] = None
    seq_no: Optional[int] = None


# Confirmed legal student status state machine transitions
LEGAL_STATUS_TRANSITIONS: Set[Tuple[str, str]] = {
    ("active", "on_leave"),
    ("active", "transferred_out"),
    ("on_leave", "active"),
    ("on_leave", "transferred_out"),
    ("transferred_out", "active"),
}
