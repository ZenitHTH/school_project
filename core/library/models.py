from dataclasses import dataclass
from typing import Optional


@dataclass
class Book:
    book_id: int
    title: str
    isbn: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    category_id: Optional[int] = None
    shelf_location: Optional[str] = None
    total_copies: int = 1
    active: int = 1


@dataclass
class BookCopy:
    copy_id: int
    book_id: int
    barcode: str
    status: str  # 'available', 'on_loan', 'lost', 'damaged', 'retired'


@dataclass
class Loan:
    loan_id: int
    copy_id: int
    student_id: int
    borrowed_at: str
    due_at: str
    returned_at: Optional[str] = None
    status: str = "active"


@dataclass
class Reservation:
    reservation_id: int
    book_id: int
    student_id: int
    reserved_at: str
    status: str  # 'waiting', 'ready', 'fulfilled', 'cancelled', 'expired'


@dataclass
class Fine:
    fine_id: int
    loan_id: int
    amount: float
    reason: str
    paid: int = 0
    paid_at: Optional[str] = None
