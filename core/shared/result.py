from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Generic, List, Optional, TypeVar, Union

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")
F = TypeVar("F")


class UnwrapFailedError(Exception):
    """Raised when unwrap() is called on an Err result."""
    pass


@dataclass
class Result(Generic[T, E]):
    """
    A Rust-inspired Result type representing either success (Ok) or failure (Err),
    along with optional warnings accumulation.
    
    Fully backward-compatible with legacy `ok`, `error`, `data` attributes,
    and `Result.success(...)` / `Result.fail(...)` class methods.
    """
    ok: bool
    error: Optional[E] = None
    data: Optional[T] = None
    warnings: List[str] = field(default_factory=list)

    # -------------------------------------------------------------------------
    # Backward compatibility class methods
    # -------------------------------------------------------------------------
    @classmethod
    def success(cls, data: Optional[T] = None, warnings: Optional[List[str]] = None) -> Result[T, Any]:
        return cls(ok=True, data=data, warnings=list(warnings or []))

    @classmethod
    def fail(cls, error: E, data: Optional[T] = None, warnings: Optional[List[str]] = None) -> Result[Any, E]:
        return cls(ok=False, error=error, data=data, warnings=list(warnings or []))

    # -------------------------------------------------------------------------
    # Rust-style inspectors
    # -------------------------------------------------------------------------
    def is_ok(self) -> bool:
        return self.ok

    def is_err(self) -> bool:
        return not self.ok

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    # -------------------------------------------------------------------------
    # Warning accumulation
    # -------------------------------------------------------------------------
    def with_warning(self, message: str) -> Result[T, E]:
        """Fluently append a warning to this result and return self."""
        self.warnings.append(message)
        return self

    def with_warnings(self, messages: List[str]) -> Result[T, E]:
        """Fluently append multiple warnings to this result and return self."""
        self.warnings.extend(messages)
        return self

    # -------------------------------------------------------------------------
    # Rust-style unwrap methods
    # -------------------------------------------------------------------------
    def unwrap(self) -> T:
        """Returns the contained Ok value or raises UnwrapFailedError."""
        if self.ok:
            return self.data  # type: ignore
        raise UnwrapFailedError(f"Called unwrap on an Err Result: {self.error}")

    def unwrap_or(self, default: T) -> T:
        """Returns the contained Ok value or a provided default."""
        if self.ok:
            return self.data  # type: ignore
        return default

    def expect(self, msg: str) -> T:
        """Returns the contained Ok value or raises UnwrapFailedError with a custom message."""
        if self.ok:
            return self.data  # type: ignore
        raise UnwrapFailedError(f"{msg}: {self.error}")

    # -------------------------------------------------------------------------
    # Rust-style combinators
    # -------------------------------------------------------------------------
    def map(self, op: Callable[[T], U]) -> Result[U, E]:
        """Maps a Result[T, E] to Result[U, E] by applying a function to a contained Ok value, leaving an Err value untouched."""
        if self.ok:
            mapped_data = op(self.data)  # type: ignore
            return Result(ok=True, data=mapped_data, error=None, warnings=list(self.warnings))
        return Result(ok=False, data=None, error=self.error, warnings=list(self.warnings))

    def map_err(self, op: Callable[[E], F]) -> Result[T, F]:
        """Maps a Result[T, E] to Result[T, F] by applying a function to a contained Err value, leaving an Ok value untouched."""
        if not self.ok:
            mapped_error = op(self.error)  # type: ignore
            return Result(ok=False, data=self.data, error=mapped_error, warnings=list(self.warnings))
        return Result(ok=True, data=self.data, error=None, warnings=list(self.warnings))

    def and_then(self, op: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Calls op if the result is Ok, returning the result. Accumulates warnings from both steps."""
        if self.ok:
            next_res = op(self.data)  # type: ignore
            combined_warnings = list(self.warnings) + list(next_res.warnings)
            return Result(
                ok=next_res.ok,
                data=next_res.data,
                error=next_res.error,
                warnings=combined_warnings,
            )
        return Result(ok=False, data=None, error=self.error, warnings=list(self.warnings))

    # -------------------------------------------------------------------------
    # Serialization helper
    # -------------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Serialize Result to dictionary for QML / JSON messaging."""
        return {
            "ok": self.ok,
            "data": self.data,
            "error": self.error,
            "warnings": self.warnings,
        }


def Ok(value: T = None, warnings: Optional[List[str]] = None) -> Result[T, Any]:
    """Convenience constructor for a successful Result."""
    return Result(ok=True, data=value, error=None, warnings=list(warnings or []))


def Err(error: E, data: Optional[T] = None, warnings: Optional[List[str]] = None) -> Result[T, E]:
    """Convenience constructor for a failed Result."""
    return Result(ok=False, data=data, error=error, warnings=list(warnings or []))
