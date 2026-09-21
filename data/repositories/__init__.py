"""Repository functions for core domain entities."""

from data.repositories import (
    book_repo,
    enrollment_repo,
    fine_repo,
    loan_repo,
    log_repo,
    reservation_repo,
    student_repo,
)

__all__ = [
    "book_repo",
    "enrollment_repo",
    "fine_repo",
    "loan_repo",
    "log_repo",
    "reservation_repo",
    "student_repo",
]