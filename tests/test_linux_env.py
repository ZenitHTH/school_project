import os
import sys
from apps.common_linux_env import setup_linux_runtime_env


def test_setup_linux_runtime_env_frozen(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delenv("GIO_MODULE_DIR", raising=False)
    monkeypatch.delenv("LIBGL_ALWAYS_SOFTWARE", raising=False)

    setup_linux_runtime_env()

    assert os.environ.get("GIO_MODULE_DIR") == ""
    assert os.environ.get("LIBGL_ALWAYS_SOFTWARE") == "1"


def test_setup_linux_runtime_env_not_frozen(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    if hasattr(sys, "frozen"):
        monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delenv("GIO_MODULE_DIR", raising=False)
    monkeypatch.delenv("LIBGL_ALWAYS_SOFTWARE", raising=False)

    setup_linux_runtime_env()

    assert "GIO_MODULE_DIR" not in os.environ
    assert os.environ.get("LIBGL_ALWAYS_SOFTWARE") == "1"


def test_setup_linux_runtime_env_preserves_custom_software_flag(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("LIBGL_ALWAYS_SOFTWARE", "0")

    setup_linux_runtime_env()

    assert os.environ.get("LIBGL_ALWAYS_SOFTWARE") == "0"


def test_setup_linux_runtime_env_non_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.delenv("GIO_MODULE_DIR", raising=False)
    monkeypatch.delenv("LIBGL_ALWAYS_SOFTWARE", raising=False)

    setup_linux_runtime_env()

    assert "GIO_MODULE_DIR" not in os.environ
    assert "LIBGL_ALWAYS_SOFTWARE" not in os.environ


def test_entrypoints_import_and_invoke_sanitizer():
    import apps.librarian_management_app.main as lib_main
    import apps.student_management_app.main as stu_main
    import apps.booth_app.main as booth_main

    assert hasattr(lib_main, "setup_linux_runtime_env")
    assert hasattr(stu_main, "setup_linux_runtime_env")
    assert hasattr(booth_main, "setup_linux_runtime_env")

