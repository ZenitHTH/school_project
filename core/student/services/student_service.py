import sqlite3
from typing import Any, Dict, List, Optional
from core.shared.result import Result
from core.student.models import LEGAL_STATUS_TRANSITIONS, Student
from data.repositories import student_repo


class StudentService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def search(
        self,
        query: str,
        grade_level: Optional[str] = None,
        room: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Result:
        """Search students matching query and optional filters."""
        try:
            rows = student_repo.search_students(
                self.conn,
                query=query,
                grade_level=grade_level,
                room=room,
                status=status,
                limit=limit,
                offset=offset,
            )
            students = [dict(row) for row in rows]
            return Result.success(students)
        except Exception as e:
            return Result.fail(f"Search failed: {e}")

    def get(self, student_id: int) -> Result:
        """Fetch student details by student_id."""
        try:
            row = student_repo.get_student(self.conn, student_id)
            if not row:
                return Result.fail(f"Student with ID {student_id} not found")
            return Result.success(dict(row))
        except Exception as e:
            return Result.fail(f"Failed to fetch student: {e}")

    def get_status(self, student_id: int) -> Optional[str]:
        """Direct current status lookup used by library loan_service."""
        row = student_repo.get_student(self.conn, student_id)
        return row["status"] if row else None

    def update_status(
        self,
        student_id: int,
        new_status: str,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> Result:
        """
        Validate and execute student status transition.
        Enforces LEGAL_STATUS_TRANSITIONS state machine.
        """
        try:
            current = student_repo.get_student(self.conn, student_id)
            if not current:
                return Result.fail(f"Student with ID {student_id} not found")

            old_status = current["status"]
            if old_status == new_status:
                return Result.fail(f"Student is already in '{new_status}' status")

            if (old_status, new_status) not in LEGAL_STATUS_TRANSITIONS:
                return Result.fail(
                    f"Illegal status transition: cannot change status from '{old_status}' to '{new_status}'"
                )

            student_repo.update_status(
                self.conn,
                student_id=student_id,
                new_status=new_status,
                reason=reason,
                actor=actor,
            )
            return Result.success({"student_id": student_id, "old_status": old_status, "new_status": new_status})
        except Exception as e:
            return Result.fail(f"Failed to update status: {e}")

    def change_student_id(
        self,
        old_id: int,
        new_id: int,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> Result:
        """Renumber student ID, propagating to all child tables."""
        if old_id == new_id:
            return Result.fail("New student ID must be different from current ID")
        try:
            existing = student_repo.get_student(self.conn, new_id)
            if existing:
                return Result.fail(f"Student ID {new_id} is already in use by another student")

            student_repo.change_student_id(
                self.conn,
                old_id=old_id,
                new_id=new_id,
                reason=reason,
                actor=actor,
            )
            return Result.success({"old_id": old_id, "new_id": new_id})
        except Exception as e:
            return Result.fail(f"Failed to change student ID: {e}")

    def update_name(
        self,
        student_id: int,
        prefix: Optional[str],
        first_name: str,
        last_name: str,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> Result:
        """Update student name and recompute full_name with audit logging."""
        if not first_name.strip() or not last_name.strip():
            return Result.fail("First name and last name cannot be empty")
        try:
            student_repo.update_name(
                self.conn,
                student_id=student_id,
                prefix=prefix,
                first_name=first_name.strip(),
                last_name=last_name.strip(),
                reason=reason,
                actor=actor,
            )
            return Result.success({"student_id": student_id})
        except Exception as e:
            return Result.fail(f"Failed to update name: {e}")

    def get_history(self, student_id: int) -> Result:
        """Get all historical audit trails for a student."""
        try:
            history = student_repo.get_student_history(self.conn, student_id)
            data = {k: [dict(r) for r in rows] for k, rows in history.items()}
            return Result.success(data)
        except Exception as e:
            return Result.fail(f"Failed to fetch student history: {e}")
