from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Result:
    ok: bool
    error: Optional[str] = None
    data: Optional[Any] = None

    @classmethod
    def success(cls, data: Optional[Any] = None) -> "Result":
        return cls(ok=True, data=data)

    @classmethod
    def fail(cls, error: str, data: Optional[Any] = None) -> "Result":
        return cls(ok=False, error=error, data=data)
