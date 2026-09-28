# Linux Mint & Ubuntu Qt/GLib Compatibility Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate startup crashes on Ubuntu/Linux Mint caused by bundled GLib/GIO symbol mismatch (`g_task_set_static_name`) and Qt GLX/OpenGL RHI failures.

**Architecture:** 
1. Packaging: Exclude bundled host GLib/GIO/GObject dynamic libraries from Linux PyInstaller bundles in `.spec` files so the executable cleanly links to host system libraries without version collision.
2. Runtime Startup: In each application's entrypoint (`main.py`), unset `GIO_MODULE_DIR` in frozen Linux runtime to block host GVFS modules from conflicting, and provide automatic software rendering fallback (`LIBGL_ALWAYS_SOFTWARE`) when running under Linux desktop environments without compatible GLX FBConfig.

**Tech Stack:** Python, PyInstaller (.spec), PySide6 / Qt 6 Quick / QML, Linux dynamic linker (glibc / glib / mesa).

**Spec:** [ubuntu-linuxmint-qt-problem.md](file:///Users/zenithth/Workspace/school_project/ubuntu-linuxmint-qt-problem.md)

## Global Constraints
- Target platforms: Linux Mint, Ubuntu, Debian derivatives, alongside macOS and Windows.
- Backward compatibility: macOS and Windows builds must remain unaffected.
- No new external runtime dependencies introduced.

## Review Focus
1. Non-frozen local developer execution on Linux must not break (e.g. running via python `apps/librarian_management_app/main.py`).
2. macOS and Windows packaging specs must ignore Linux-only binary exclusions.
3. User-defined `LIBGL_ALWAYS_SOFTWARE` or `QT_QUICK_BACKEND` environment variables must take precedence if explicitly configured by the user.
4. CLI-only mode (`--cli` or non-GUI test harnesses) must function without requiring OpenGL/GLX.
5. Unit tests for startup environment configuration must pass cleanly on all environments.

---

### Task 1: Add linux runtime startup environment sanitize helper

**Files:**
- Create: `apps/common_linux_env.py`
- Test: `tests/test_linux_env.py`

**Interfaces:**
- Consumes: `os.environ`, `sys.platform`, `getattr(sys, "frozen", False)`
- Produces: `setup_linux_runtime_env() -> None`

- [ ] **Step 1: Write test for linux runtime env configuration**

```python
import os
import sys
from apps.common_linux_env import setup_linux_runtime_env

def test_setup_linux_runtime_env(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delenv("GIO_MODULE_DIR", raising=False)
    
    setup_linux_runtime_env()
    assert os.environ.get("GIO_MODULE_DIR") == ""
    assert os.environ.get("LIBGL_ALWAYS_SOFTWARE") == "1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_linux_env.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'apps.common_linux_env'`

- [ ] **Step 3: Implement `setup_linux_runtime_env()` in `apps/common_linux_env.py`**

Provide safe environment sanitation:
- Clear `GIO_MODULE_DIR` when `frozen` and `platform.startswith("linux")`.
- Default `LIBGL_ALWAYS_SOFTWARE="1"` if not already set by caller, preventing Qt Quick GLX aborts.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_linux_env.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/common_linux_env.py tests/test_linux_env.py
git commit -m "feat(linux): add runtime environment sanitizer for linux frozen bundles"
```

---

### Task 2: Integrate runtime environment sanitize into all application entrypoints

**Files:**
- Modify: `apps/librarian_management_app/main.py`
- Modify: `apps/student_management_app/main.py`
- Modify: `apps/booth_app/main.py`
- Test: `tests/test_linux_env.py`

**Interfaces:**
- Consumes: `setup_linux_runtime_env()` from `apps.common_linux_env`
- Produces: Entrypoints sanitized before Qt / GIO initialization

- [ ] **Step 1: Add tests verifying entrypoints call environment sanitizer**

```python
def test_entrypoints_import_and_invoke_sanitizer():
    import apps.librarian_management_app.main as lib_main
    import apps.student_management_app.main as stu_main
    import apps.booth_app.main as booth_main
    assert hasattr(lib_main, "setup_linux_runtime_env")
    assert hasattr(stu_main, "setup_linux_runtime_env")
    assert hasattr(booth_main, "setup_linux_runtime_env")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_linux_env.py::test_entrypoints_import_and_invoke_sanitizer -v`
Expected: FAIL

- [ ] **Step 3: Hook `setup_linux_runtime_env()` in the three `main.py` files**

Call `setup_linux_runtime_env()` before `QGuiApplication` or Qt imports execute.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_linux_env.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/librarian_management_app/main.py apps/student_management_app/main.py apps/booth_app/main.py tests/test_linux_env.py
git commit -m "fix(linux): invoke setup_linux_runtime_env in all app entrypoints"
```

---

### Task 3: Exclude conflicting GLib/GIO binaries in PyInstaller Linux spec files

**Files:**
- Modify: `packaging/librarian_management.spec`
- Modify: `packaging/student_management.spec`
- Modify: `packaging/booth_app.spec`
- Test: `tests/test_spec_exclusions.py`

**Interfaces:**
- Consumes: `a.binaries`
- Produces: Filtered `a.binaries` excluding `libglib*`, `libgio*`, `libgobject*`, `libgmodule*` on Linux

- [ ] **Step 1: Write test to verify spec binary filter logic**

Test helper filter function ensuring target `.so` libraries are stripped from binary tuples:
```python
def test_binary_exclusion_filter():
    binaries = [
        ("libglib-2.0.so.0", "/path", "BINARY"),
        ("libgio-2.0.so.0", "/path", "BINARY"),
        ("libsqlite3.so.0", "/path", "BINARY")
    ]
    # Filter test ensuring libsqlite3 is kept while libglib/libgio are pruned
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_spec_exclusions.py -v`
Expected: FAIL

- [ ] **Step 3: Update `packaging/*.spec` files with binary filter**

Filter `a.binaries` on Linux:
```python
if sys.platform.startswith("linux"):
    EXCLUDE_PREFIXES = ('libglib', 'libgio', 'libgobject', 'libgmodule')
    a.binaries = [
        x for x in a.binaries
        if not any(os.path.basename(x[0]).lower().startswith(p) for p in EXCLUDE_PREFIXES)
    ]
```

- [ ] **Step 4: Run tests to verify**

Run: `pytest tests/test_spec_exclusions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packaging/librarian_management.spec packaging/student_management.spec packaging/booth_app.spec tests/test_spec_exclusions.py
git commit -m "fix(packaging): exclude bundled host GLib/GIO libraries from Linux PyInstaller specs"
```

---

### Task 4: Regression suite run & documentation update

**Files:**
- Modify: `ubuntu-linuxmint-qt-problem.md`
- Test: Full test suite (`pytest`)

- [ ] **Step 1: Run full test suite**

Run: `pytest`
Expected: All tests pass.

- [ ] **Step 2: Update `ubuntu-linuxmint-qt-problem.md` with resolved status**

Document that the root causes have been resolved in source code and packaging specifications.

- [ ] **Step 3: Commit**

```bash
git add ubuntu-linuxmint-qt-problem.md
git commit -m "docs: document source-level fixes for Linux Mint/Ubuntu Qt and GLib issues"
```
