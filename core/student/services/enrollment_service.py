import re
import sqlite3
from typing import Any, Dict, List, Optional
from core.shared.result import Result
from data.repositories import enrollment_repo, student_repo


GRADE_MAP = {
    "ม.1": "ม.2",
    "ม.2": "ม.3",
    "ม.3": "ม.4",
    "ม.4": "ม.5",
    "ม.5": "ม.6",
}


class EnrollmentService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def current_enrollment(self, student_id: int) -> Result:
        """Fetch current period enrollment for a student."""
        try:
            row = enrollment_repo.get_current_enrollment(self.conn, student_id)
            if not row:
                return Result.fail(f"No current enrollment found for student {student_id}")
            return Result.success(dict(row))
        except Exception as e:
            return Result.fail(f"Failed to fetch enrollment: {e}")

    def change_classroom(
        self,
        student_id: int,
        new_room: int,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> Result:
        """Move student to a different room in the current period and log reason."""
        try:
            current = enrollment_repo.get_current_enrollment(self.conn, student_id)
            if not current:
                return Result.fail(f"Student {student_id} is not currently enrolled in any class")

            if current["room"] == new_room:
                return Result.fail(f"Student is already in room {new_room}")

            enrollment_repo.change_classroom(
                self.conn,
                student_id=student_id,
                new_room=new_room,
                reason=reason,
                actor=actor,
            )
            return Result.success({"student_id": student_id, "old_room": current["room"], "new_room": new_room})
        except Exception as e:
            return Result.fail(f"Failed to change classroom: {e}")

    def enroll_next_period(
        self,
        student_id: int,
        academic_year: int,
        semester: int,
        grade_level: str,
        room: int,
        track: Optional[str] = None,
        seq_no: Optional[int] = None,
        actor: Optional[str] = None,
    ) -> Result:
        """Enroll student into a new academic period."""
        try:
            enr_id = enrollment_repo.enroll_next_period(
                self.conn,
                student_id=student_id,
                academic_year=academic_year,
                semester=semester,
                grade_level=grade_level,
                room=room,
                track=track,
                seq_no=seq_no,
                actor=actor,
            )
            return Result.success({"enrollment_id": enr_id})
        except sqlite3.IntegrityError:
            return Result.fail(
                f"Student {student_id} is already enrolled in {grade_level}/{room} for {academic_year}/{semester}"
            )
        except Exception as e:
            return Result.fail(f"Failed to enroll student: {e}")

    def get_class_roster(
        self,
        academic_year: int,
        semester: int,
        grade_level: str,
        room: int,
    ) -> Result:
        """List all students in a class."""
        try:
            rows = enrollment_repo.get_class_roster(
                self.conn,
                academic_year=academic_year,
                semester=semester,
                grade_level=grade_level,
                room=room,
            )
            return Result.success([dict(r) for r in rows])
        except Exception as e:
            return Result.fail(f"Failed to fetch class roster: {e}")

    def get_class_statistics(self) -> Result:
        """Fetch gender breakdown and class totals."""
        try:
            rows = enrollment_repo.get_class_statistics(self.conn)
            return Result.success([dict(r) for r in rows])
        except Exception as e:
            return Result.fail(f"Failed to fetch class statistics: {e}")

    def promote_students(
        self,
        source_year: int,
        source_semester: int,
        target_year: int,
        target_semester: int,
        actor: Optional[str] = None,
    ) -> Result:
        """
        Year-end bulk promotion for active students.
        Promotes ม.1->ม.2, ม.2->ม.3, etc. All in one transaction.
        """
        cur = self.conn.cursor()
        sql = """
            SELECT e.student_id, e.grade_level, e.room, e.track, s.status
            FROM enrollments e
            JOIN students s ON s.student_id = e.student_id
            WHERE e.academic_year = ? AND e.semester = ? AND s.status = 'active'
        """
        students = cur.execute(sql, (source_year, source_semester)).fetchall()
        if not students:
            return Result.fail(f"No active enrollments found for {source_year}/{source_semester}")

        promoted_count = 0
        graduated_count = 0

        with self.conn:
            for s in students:
                curr_grade = s["grade_level"]
                if curr_grade in GRADE_MAP:
                    next_grade = GRADE_MAP[curr_grade]
                    enrollment_repo.enroll_next_period(
                        self.conn,
                        student_id=s["student_id"],
                        academic_year=target_year,
                        semester=target_semester,
                        grade_level=next_grade,
                        room=s["room"],
                        track=s["track"],
                        actor=actor,
                    )
                    promoted_count += 1
                else:
                    # ม.6 graduates
                    graduated_count += 1

        return Result.success({
            "promoted_count": promoted_count,
            "graduated_count": graduated_count,
            "target_period": f"{target_year}/{target_semester}",
        })
