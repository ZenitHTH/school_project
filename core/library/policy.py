from dataclasses import dataclass


@dataclass
class LibraryPolicy:
    """Configurable library business rules."""
    loan_duration_days: int = 14
    max_active_loans: int = 3
    max_renewals: int = 1
    overdue_fine_per_day: float = 5.0
    max_overdue_fine: float = 200.0
    unpaid_fines_threshold: float = 50.0
    lost_book_fee: float = 150.0


DEFAULT_POLICY = LibraryPolicy()
