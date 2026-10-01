# Rust-Style Result Type (`core/shared/result.py`)

## Motivation
In earlier versions, operations returned basic dataclasses or threw exceptions across layers. The new Rust-inspired `Result[T, E]` provides:
1. Explicit success (`Ok`) and failure (`Err`) states.
2. Accumulation of non-fatal warnings (e.g., spelling differences or missing optional attributes).
3. Monadic combinators (`map`, `map_err`, `and_then`) and unwrap methods.
4. 100% backward-compatibility with legacy properties (`ok`, `data`, `error`).

---

## API Summary

```python
from core.shared.result import Ok, Err, Result, UnwrapFailedError

# 1. Constructors
res_ok = Ok("value", warnings=["non-critical warning"])
res_err = Err("error message", data=None, warnings=["context"])

# Legacy factory methods (100% compatible)
res_leg = Result.success(data="legacy")
res_fail = Result.fail(error="failed")

# 2. Inspectors
res.is_ok() -> bool
res.is_err() -> bool
res.has_warnings() -> bool
res.warnings -> List[str]

# 3. Warning Accumulators
res.with_warning("new warning message")
res.with_warnings(["w1", "w2"])

# 4. Unwraps
res.unwrap() -> T                  # Raises UnwrapFailedError on Err
res.unwrap_or(default: T) -> T     # Returns default on Err
res.expect("Custom msg") -> T      # Raises UnwrapFailedError with custom message

# 5. Combinators
res.map(lambda x: x * 2)           # Transforms data if Ok, keeps Err & warnings
res.map_err(lambda e: f"Err: {e}") # Transforms error if Err
res.and_then(fn)                   # Chains function returning Result; merges warnings from both steps

# 6. Serialization
res.to_dict() -> {"ok": bool, "data": Any, "error": Optional[str], "warnings": List[str]}
```

---

## Integration in Codebase
- **Excel Roster Importer (`core/importers/xlsx_diff_importer.py`)**: Emits warnings when names differ slightly (`identity_conflicts`) or when active students are missing from the incoming spreadsheet.
- **Adapters (`apps/student_management_app/adapters/student_admin_adapter.py`)**: Serializes `"warnings": res.warnings` into JSON payload returned to QML.
