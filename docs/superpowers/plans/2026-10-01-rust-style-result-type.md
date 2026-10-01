# Rust-Style Result Type with Warnings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `core/shared/result.py` to a Rust-inspired, type-safe, generic `Result[T, E]` type supporting Ok, Err, Warnings, pattern-matching, combinators (`map`, `and_then`, `unwrap_or`), and 100% backward-compatibility with existing dictionary-like `ok`, `error`, `data`, `.success()`, and `.fail()`.

**Architecture:** 
1. `core/shared/result.py`: Define `Result[T, E]`, `Ok[T]`, `Err[E]`, with list of `warnings: List[str]`, `.unwrap()`, `.unwrap_or()`, `.map()`, `.map_err()`, `.and_then()`, `.with_warning()`, and `to_dict()`.
2. Existing codebase compatibility: Retain `Result.success(data=...)` and `Result.fail(error=..., data=...)` factories, and attributes `res.ok`, `res.error`, `res.data`, `res.warnings`.
3. Adapter & JSON Serialization: Add `.to_dict()` and update adapters to seamlessly serialize `{"ok": bool, "data": ..., "error": ..., "warnings": [...]}` to QML.

**Tech Stack:** Python 3.14 (Generic types, dataclasses, typing.Union), PySide6, pytest.

## Global Constraints
- **Zero breaking changes**: All existing service calls (`Result.success(...)`, `Result.fail(...)`) and boolean checks (`if res.ok:`, `if not res.ok:`, `res.data`, `res.error`) across `core/`, `apps/`, and `tests/` must work without code changes.
- **Rust-style ergonomics**:
  - `Ok(value, warnings=[...])` and `Err(error, warnings=[...])` constructors.
  - `.is_ok()`, `.is_err()`, `.has_warnings()`.
  - `.unwrap()` (raises `UnwrapFailedError` on Err, including error message).
  - `.unwrap_or(default)` (returns default if Err).
  - `.map(fn)` (transforms data if Ok, preserves Err and warnings).
  - `.and_then(fn)` (flat-maps returning a new Result, accumulating warnings).
  - `.with_warning(msg)` (fluent warning accumulator).
- **100% test pass**: All 177 unit & UI integration tests must pass.

---

### Task 1: Implement Rust-style Generic Result with Warnings in `core/shared/result.py`

**Files:**
- Modify: `core/shared/result.py`
- Create: `tests/test_result_type.py`

**Interfaces:**
- Consumes: Python typing (`Generic`, `TypeVar`, `Optional`, `List`, `Callable`, `Any`).
- Produces: `Result[T, E]`, `Ok(value, warnings=None)`, `Err(error, data=None, warnings=None)`, methods `unwrap()`, `unwrap_or()`, `expect()`, `map()`, `map_err()`, `and_then()`, `with_warning()`, `has_warnings()`, and properties `ok`, `error`, `data`, `warnings`.

- [x] **Step 1: Write failing tests in `tests/test_result_type.py`**
Test Rust methods:
- `res = Ok(42).with_warning("deprecated usage")` -> `res.is_ok() is True`, `res.unwrap() == 42`, `res.warnings == ["deprecated usage"]`.
- `res = Err("disk full")` -> `res.is_err() is True`, `res.unwrap_or(0) == 0`, `res.unwrap()` raises `UnwrapFailedError`.
- Combinator chaining: `Ok(10).map(lambda x: x * 2).and_then(lambda x: Ok(x + 5).with_warning("warn 1"))` accumulates warnings and yields `25`.
- Backward compatibility: `Result.success("foo")` -> `res.ok is True`, `res.data == "foo"`, `res.error is None`, `res.warnings == []`.
- Backward compatibility: `Result.fail("bad")` -> `res.ok is False`, `res.error == "bad"`.

- [x] **Step 2: Run test to verify it fails**
Run: `.venv/bin/pytest tests/test_result_type.py`
Expected: FAIL.

- [x] **Step 3: Implement `Result[T, E]`, `Ok`, and `Err` in `core/shared/result.py`**
Include full combinator methods, warning list accumulator, and compatibility properties.

- [x] **Step 4: Run test to verify it passes**
Run: `.venv/bin/pytest tests/test_result_type.py`
Expected: PASS.

- [x] **Step 5: Run existing repo test suite**
Run: `.venv/bin/pytest tests/`
Expected: All 177+ tests pass without breaking existing service calls.

- [x] **Step 6: Commit**
```bash
git add core/shared/result.py tests/test_result_type.py
git commit -m "feat(core): implement Rust-inspired Result[T, E] with warnings and combinators"
```

---

### Task 2: Integrate Warnings and Combinators into Core Services & Adapters

**Files:**
- Modify: `core/importers/xlsx_diff_importer.py`
- Modify: `apps/student_management_app/adapters/student_admin_adapter.py`
- Modify: `apps/librarian_management_app/adapters/librarian_admin_adapter.py`
- Test: `tests/test_adapters.py`
- Test: `tests/test_xlsx_diff_importer.py`

**Interfaces:**
- Consumes: `Result[T, E]`, `Ok`, `Err` with warnings.
- Produces: Adapters returning JSON serialization containing `"warnings": [...]` when warnings exist.

- [x] **Step 1: Write test for warnings propagation in `tests/test_adapters.py`**
Verify that service results with warnings are serialized to JSON with a `"warnings"` key.

- [x] **Step 2: Add warning detection in `core/importers/xlsx_diff_importer.py`**
When `identity_conflicts` or `missing_students` exist during Excel diffing or applying, attach warnings via `.with_warning(...)`.

- [x] **Step 3: Update `to_dict()` serialization helper in adapters**
Ensure JSON output from adapter slots includes `"warnings": res.warnings`.

- [x] **Step 4: Run tests**
Run: `.venv/bin/pytest tests/test_adapters.py tests/test_xlsx_diff_importer.py`
Expected: PASS.

- [x] **Step 5: Commit**
```bash
git add core/importers/ apps/ tests/
git commit -m "feat(services): propagate warnings through Result to UI adapters"
```

---

### Task 3: Full Regression Verification

**Files:**
- Test: `pytest tests/`

- [x] **Step 1: Run complete test suite**
Run: `.venv/bin/pytest tests/`
Expected: 100% pass across all test modules.

- [x] **Step 2: Commit documentation & finish**
```bash
git commit -m "docs: finalize Rust-style Result type plan and implementation"
```
