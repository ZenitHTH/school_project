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


def test_installer_iss_has_per_app_id_and_rpm_sanitizes_hyphen_version():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    iss_path = os.path.join(repo_root, "packaging", "installers", "windows", "installer.iss")
    with open(iss_path, "r", encoding="utf-8") as f:
        iss_content = f.read()
    assert "AppId={{C78DFE32-0941-4E7B-BFA6-92AE8997321F}-{#AppName}" in iss_content

    rpm_path = os.path.join(repo_root, "packaging", "installers", "rpm", "build_rpm.sh")
    with open(rpm_path, "r", encoding="utf-8") as f:
        rpm_content = f.read()
    assert 'RPM_VERSION="${VERSION//-/~}"' in rpm_content
    assert "Version:        $RPM_VERSION" in rpm_content


def test_ci_and_release_workflows_follow_standard_release_pipeline():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    workflows_dir = os.path.join(repo_root, ".github", "workflows")

    assert not os.path.exists(os.path.join(workflows_dir, "build.yml")), "Legacy build.yml must be removed"
    ci_path = os.path.join(workflows_dir, "ci.yml")
    rel_path = os.path.join(workflows_dir, "release.yml")
    assert os.path.exists(ci_path), "ci.yml missing"
    assert os.path.exists(rel_path), "release.yml missing"

    with open(ci_path, "r", encoding="utf-8") as f:
        ci_yml = f.read()
    assert "pull_request:" in ci_yml
    assert "pytest" in ci_yml
    assert "cache: 'pip'" in ci_yml

    with open(rel_path, "r", encoding="utf-8") as f:
        rel_yml = f.read()
    assert "- 'v*.*.*'" in rel_yml
    assert "workflow_dispatch:" in rel_yml
    assert "needs: [test]" in rel_yml
    assert "ditto -c -k --sequesterRsrc --keepParent" in rel_yml
    assert "SHA256SUMS.txt" in rel_yml
    assert "generate_release_notes: true" in rel_yml
    assert "startsWith(github.ref, 'refs/tags/v')" in rel_yml


def test_package_scripts_and_release_checksum_integrity():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Test debian pre-release version sanitization
    deb_path = os.path.join(repo_root, "packaging", "installers", "deb", "build_deb.sh")
    with open(deb_path, "r", encoding="utf-8") as f:
        deb_content = f.read()
    assert 'DEB_VERSION="${VERSION//-/~}"' in deb_content
    assert "Version: $DEB_VERSION" in deb_content

    # Test release workflow does not self-include SHA256SUMS.txt
    rel_path = os.path.join(repo_root, ".github", "workflows", "release.yml")
    with open(rel_path, "r", encoding="utf-8") as f:
        rel_yml = f.read()
    assert "sha256sum * > SHA256SUMS.txt" not in rel_yml
    assert "sha256sum * > ../SHA256SUMS.txt" in rel_yml

