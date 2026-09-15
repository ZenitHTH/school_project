import datetime
import sqlite3
from typing import Any, Dict, List, Optional
from core.shared.result import Result
from core.library.policy import DEFAULT_POLICY, LibraryPolicy
from core.library.services.fine_service import FineService
from core.library.services.reservation_service import ReservationService
from core.student.services.student_service import StudentService
from data.repositories import book_repo, loan_repo, reservation_repo, student_repo


class LoanService:
    def __init__(
        self,
        conn: sqlite3.Connection,
        policy: LibraryPolicy = DEFAULT_POLICY,
        fine_service: Optional[FineService] = None,
        reservation_service: Optional[ReservationService] = None,
        student_service: Optional[StudentService] = None,
    ):
        self.conn = conn
        self.policy = policy
        self.fine_service = fine_service or FineService(conn, policy)
        self.reservation_service = reservation_service or ReservationService(conn)
        self.student_service = student_service or StudentService(conn)

    def checkout(
        self,
        student_id: int,
        book_id: Optional[int] = None,
        barcode: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> Result:
        """
        Process book checkout with all policy and student status validations.
        """
        # 1. Student Status validation
        student_status = self.student_service.get_status(student_id)
        if not student_status:
            return Result.fail(f"Student {student_id} not found in local system")
        if student_status != "active":
            return Result.fail(
                f"Borrowing refused: student status is '{student_status}' (must be 'active')"
            )

        # 2. Unpaid fines check
        unpaid = self.fine_service.get_unpaid_total(student_id)
        if unpaid > self.policy.unpaid_fines_threshold:
            return Result.fail(
                f"Borrowing blocked: student has {unpaid:.2f} THB unpaid fines (threshold: {self.policy.unpaid_fines_threshold:.2f} THB)"
            )

        # 3. Active loans limit
        active_loans = loan_repo.get_active_loans_count(self.conn, student_id)
        if active_loans >= self.policy.max_active_loans:
            return Result.fail(
                f"Borrowing limit reached: student already has {active_loans} active loan(s) (maximum: {self.policy.max_active_loans})"
            )

        # 4. Resolve copy
        copy = None
        if barcode:
            copy = book_repo.get_copy_by_barcode(self.conn, barcode)
            if not copy:
                return Result.fail(f"No copy found with barcode '{barcode}'")
            if not copy["active"]:
                return Result.fail(f"Book '{copy['title']}' is retired")
            if copy["status"] != "available":
                return Result.fail(f"Copy with barcode '{barcode}' is not available (status: {copy['status']})")
        elif book_id is not None:
            copy = book_repo.get_available_copy(self.conn, book_id)
            if not copy:
                return Result.fail(f"No available copies for book ID {book_id}")
        else:
            return Result.fail("Either barcode or book_id must be provided for checkout")

        # 5. Check if student had a ready reservation for this book
        cur = self.conn.cursor()
        cur.execute(
            "SELECT reservation_id FROM reservations WHERE book_id = ? AND student_id = ? AND status = 'ready' LIMIT 1",
            (copy["book_id"], student_id),
        )
        res_row = cur.fetchone()
        if res_row:
            self.reservation_service.fulfill(res_row["reservation_id"], actor=actor)

        # 6. Issue loan
        now = datetime.datetime.now(datetime.timezone.utc)
        borrowed_at = now.isoformat()
        due_at = (now + datetime.timedelta(days=self.policy.loan_duration_days)).isoformat()

        try:
            loan_id = loan_repo.create_loan(
                self.conn,
                copy_id=copy["copy_id"],
                student_id=student_id,
                borrowed_at=borrowed_at,
                due_at=due_at,
                actor=actor,
            )
            return Result.success({
                "loan_id": loan_id,
                "copy_id": copy["copy_id"],
                "student_id": student_id,
                "due_at": due_at,
            })
        except Exception as e:
            return Result.fail(f"Failed to complete checkout: {e}")

    def return_book(
        self,
        loan_id: int,
        returned_at: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> Result:
        """
        Process book return, calculate overdue fines, and promote waiting reservations.
        """
        loan = loan_repo.get_loan(self.conn, loan_id)
        if not loan:
            return Result.fail(f"Loan {loan_id} not found")
        if loan["status"] == "returned":
            return Result.fail(f"Loan {loan_id} has already been returned")

        now = datetime.datetime.now(datetime.timezone.utc)
        return_time = returned_at or now.isoformat()

        try:
            loan_repo.return_loan(self.conn, loan_id=loan_id, returned_at=return_time, actor=actor)

            # Check overdue
            fine_info = None
            try:
                due_dt = datetime.datetime.fromisoformat(loan["due_at"])
                ret_dt = datetime.datetime.fromisoformat(return_time)
                if ret_dt > due_dt:
                    days_late = (ret_dt.date() - due_dt.date()).days
                    if days_late > 0:
                        res_fine = self.fine_service.assess_overdue(loan_id, days_late, actor=actor)
                        if res_fine.ok:
                            fine_info = res_fine.data
            except Exception as fine_exc:
                import sys
                print(
                    f"[WARN] Fine calculation failed for loan {loan_id}: {fine_exc}",
                    file=sys.stderr,
                )

            # Promote next waiting reservation if any
            promoted_res = self.reservation_service.promote_next(loan["book_id"], actor=actor)

            return Result.success({
                "loan_id": loan_id,
                "returned_at": return_time,
                "fine": fine_info,
                "reservation_promoted": promoted_res is not None,
            })
        except Exception as e:
            return Result.fail(f"Failed to return book: {e}")

    def renew(self, loan_id: int, actor: Optional[str] = None) -> Result:
        """Extend due date if loan is active and not reserved by others."""
        loan = loan_repo.get_loan(self.conn, loan_id)
        if not loan:
            return Result.fail(f"Loan {loan_id} not found")
        if loan["status"] != "active":
            return Result.fail(f"Cannot renew loan in '{loan['status']}' status")

        if self.reservation_service.has_waiting(loan["book_id"]):
            return Result.fail("Cannot renew: another student has an active reservation for this book")

        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            due_dt = datetime.datetime.fromisoformat(loan["due_at"])
            new_due = (due_dt + datetime.timedelta(days=self.policy.loan_duration_days)).isoformat()
            loan_repo.renew_loan(self.conn, loan_id=loan_id, new_due_at=new_due, actor=actor)
            return Result.success({"loan_id": loan_id, "new_due_at": new_due})
        except Exception as e:
            return Result.fail(f"Failed to renew loan: {e}")

    def get_active_loans(self) -> Result:
        """Fetch all active and overdue loans."""
        try:
            rows = loan_repo.get_active_loans(self.conn)
            return Result.success([dict(r) for r in rows])
        except Exception as e:
            return Result.fail(f"Failed to fetch active loans: {e}")

    def get_overdue_loans(self) -> Result:
        """Fetch loans currently overdue."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            rows = loan_repo.get_overdue_loans(self.conn, now_iso)
            return Result.success([dict(r) for r in rows])
        except Exception as e:
            return Result.fail(f"Failed to fetch overdue loans: {e}")

    def get_student_history(self, student_id: int) -> Result:
        """Get loan history for a student."""
        try:
            rows = loan_repo.get_student_loan_history(self.conn, student_id)
            return Result.success([dict(r) for r in rows])
        except Exception as e:
            return Result.fail(f"Failed to fetch student loan history: {e}")

    def get_copy_history(self, copy_id: int) -> Result:
        """Get lending history for a specific book copy."""
        try:
            rows = loan_repo.get_book_copy_loan_history(self.conn, copy_id)
            return Result.success([dict(r) for r in rows])
        except Exception as e:
            return Result.fail(f"Failed to fetch copy loan history: {e}")
