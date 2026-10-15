import os


def filter_linux_binaries(binaries):
    exclude_prefixes = ("libglib", "libgio", "libgobject", "libgmodule")
    return [
        x for x in binaries
        if not any(os.path.basename(x[0]).lower().startswith(p) for p in exclude_prefixes)
    ]


def test_filter_linux_binaries():
    sample_binaries = [
        ("libglib-2.0.so.0", "/usr/lib/libglib-2.0.so.0", "BINARY"),
        ("libgio-2.0.so.0", "/usr/lib/libgio-2.0.so.0", "BINARY"),
        ("libgobject-2.0.so.0", "/usr/lib/libgobject-2.0.so.0", "BINARY"),
        ("libgmodule-2.0.so.0", "/usr/lib/libgmodule-2.0.so.0", "BINARY"),
        ("libsqlite3.so.0", "/usr/lib/libsqlite3.so.0", "BINARY"),
        ("libcrypto.so.3", "/usr/lib/libcrypto.so.3", "BINARY"),
    ]

    filtered = filter_linux_binaries(sample_binaries)
    names = [x[0] for x in filtered]

    assert "libsqlite3.so.0" in names
    assert "libcrypto.so.3" in names
    assert "libglib-2.0.so.0" not in names
    assert "libgio-2.0.so.0" not in names
    assert "libgobject-2.0.so.0" not in names
    assert "libgmodule-2.0.so.0" not in names


def test_build_rpm_script_uses_absolute_path():
    script_path = os.path.join(os.path.dirname(__file__), "..", "packaging", "installers", "rpm", "build_rpm.sh")
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "ABS_DIST_BIN_PATH=" in content
    assert 'cp "$ABS_DIST_BIN_PATH"' in content


def test_dead_files_and_duplicate_docs_removed():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    removed_paths = [
        "application_layer_design.md",
        "database_layer_design.md",
        "design_doc.md",
        "ui_layer_design.md",
        "query_lm_studio.py",
        "seed_sample_students.py",
        "packaging/booth_app_windows.spec",
        "packaging/librarian_management_windows.spec",
        "packaging/student_management_windows.spec",
        "core/library/models.py",
        "core/shared/errors.py",
    ]
    for rel in removed_paths:
        assert not os.path.exists(os.path.join(repo_root, rel)), f"Dead file still exists: {rel}"

    # Canonical files must remain
    for kept in [
        "doc/design_doc.md",
        "wiki/index.md",
        "packaging/librarian_management.spec",
        "packaging/student_management.spec",
        "packaging/booth_app.spec",
        "core/student/models.py",
        "core/shared/result.py",
    ]:
        assert os.path.exists(os.path.join(repo_root, kept)), f"Required file missing: {kept}"

