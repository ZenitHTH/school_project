import datetime
import sqlite3
from typing import List, Optional
from core.shared.result import Result
from core.library.policy import DEFAULT_POLICY, LibraryPolicy
from data.repositories import fine_repo


class FineService:
    def __init__(self, conn: sqlite3.Connection, policy: LibraryPolicy = DEFAULT_POLICY):
        self.conn = conn
        self.policy = policy

    def assess_overdue(
        self,
        loan_id: int,
        days_overdue: int,
        actor: Optional[str] = None,
    ) -> Result:
        """Calculate and assess overdue fine capped by max_overdue_fine."""
        if days_overdue <= 0:
            return Result.success(None)
        raw_amount = days_overdue * self.policy.overdue_fine_per_day
        final_amount = min(raw_amount, self.policy.max_overdue_fine)

        try:
            fine_id = fine_repo.create_fine(
                self.conn,
                loan_id=loan_id,
                amount=final_amount,
                reason=f"Overdue by {days_overdue} day(s)",
                actor=actor,
            )
            return Result.success({"fine_id": fine_id, "amount": final_amount})
        except Exception as e:
            return Result.fail(f"Failed to assess fine: {e}")

    def assess_lost_book(
        self,
        loan_id: int,
        custom_amount: Optional[float] = None,
        actor: Optional[str] = None,
    ) -> Result:
        """Assess lost book replacement fee."""
        amount = custom_amount if custom_amount is not None else self.policy.lost_book_fee
        try:
            fine_id = fine_repo.create_fine(
                self.conn,
                loan_id=loan_id,
                amount=amount,
                reason="Lost book fee",
                actor=actor,
            )
            return Result.success({"fine_id": fine_id, "amount": amount})
        except Exception as e:
            return Result.fail(f"Failed to assess lost book fee: {e}")

    def record_payment(self, fine_id: int, actor: Optional[str] = None) -> Result:
        """Mark fine paid."""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            fine_repo.record_payment(self.conn, fine_id=fine_id, paid_at=now_iso, actor=actor)
            return Result.success({"fine_id": fine_id, "paid_at": now_iso})
        except Exception as e:
            return Result.fail(f"Failed to record fine payment: {e}")

    def get_unpaid_total(self, student_id: int) -> float:
        """Get total unpaid fine balance for student."""
        return fine_repo.get_unpaid_fines_total(self.conn, student_id)

    def list_fines(self, paid: Optional[bool] = None) -> Result:
        """List all fines."""
        try:
            rows = fine_repo.list_fines(self.conn, paid=paid)
            return Result.success([dict(r) for r in rows])
        except Exception as e:
            return Result.fail(f"Failed to list fines: {e}")
