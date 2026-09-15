import datetime
import sqlite3
from typing import List, Optional
from core.shared.result import Result
from data.repositories import book_repo, reservation_repo


class ReservationService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def reserve(self, student_id: int, book_id: int, actor: Optional[str] = None) -> Result:
        """
        Reserve a book.
        Allowed only when no physical copy of the book is currently available.
        """
        try:
            # Check book exists and active
            book = book_repo.get_book(self.conn, book_id)
            if not book or not book["active"]:
                return Result.fail(f"Book {book_id} is not active or does not exist")

            # Check if any copy is currently available
            avail = book_repo.get_available_copy(self.conn, book_id)
            if avail:
                return Result.fail(
                    "Physical copies are currently available on shelf; checkout directly instead of reserving."
                )

            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            res_id = reservation_repo.create_reservation(
                self.conn,
                book_id=book_id,
                student_id=student_id,
                reserved_at=now_iso,
                actor=actor,
            )
            return Result.success({"reservation_id": res_id, "book_id": book_id, "student_id": student_id})
        except Exception as e:
            return Result.fail(f"Failed to create reservation: {e}")

    def cancel(self, reservation_id: int, actor: Optional[str] = None) -> Result:
        """Cancel a reservation."""
        try:
            reservation_repo.cancel_reservation(self.conn, reservation_id, actor=actor)
            return Result.success({"reservation_id": reservation_id})
        except Exception as e:
            return Result.fail(f"Failed to cancel reservation: {e}")

    def promote_next(self, book_id: int, actor: Optional[str] = None) -> Optional[int]:
        """Move next queued reservation from waiting to ready."""
        return reservation_repo.promote_next_reservation(self.conn, book_id=book_id, actor=actor)

    def fulfill(self, reservation_id: int, actor: Optional[str] = None) -> Result:
        """Mark reservation fulfilled upon student checkout."""
        try:
            reservation_repo.fulfill_reservation(self.conn, reservation_id, actor=actor)
            return Result.success({"reservation_id": reservation_id})
        except Exception as e:
            return Result.fail(f"Failed to fulfill reservation: {e}")

    def has_waiting(self, book_id: int) -> bool:
        """Check if any active reservation is queued for this book."""
        return reservation_repo.has_waiting_reservation(self.conn, book_id)

    def list_reservations(self, status: Optional[str] = None) -> Result:
        """List reservations."""
        try:
            rows = reservation_repo.list_reservations(self.conn, status=status)
            return Result.success([dict(r) for r in rows])
        except Exception as e:
            return Result.fail(f"Failed to list reservations: {e}")
