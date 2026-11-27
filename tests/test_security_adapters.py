"""Security regression tests for QML adapters, path validation, PDF export, and Booth discovery."""

import json
import os
import stat
from pathlib import Path

import pytest

from apps.booth_app.adapters.booth_adapter import BoothAdapter
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter
from apps.student_management_app.adapters.student_admin_adapter import StudentAdminAdapter
from core.network.booth_config import DEFAULT_LAN_PORT
from core.network.lan_client import BoothLanClient
from core.network.lan_server import BoothLanServer
from data.db import get_connection
from data.migrate import apply_migrations


def _open_migrated_file_db(db_path: Path):
    conn = get_connection(str(db_path), pin="123456")
    apply_migrations(conn)
    return conn


def test_student_adapter_rejects_live_db_overwrite_and_bad_paths(tmp_path):
    db_file = tmp_path / "student_live.sqlite"
    conn = _open_migrated_file_db(db_file)
    try:
        adapter = StudentAdminAdapter(conn)

        # Cannot overwrite active app SQLite DB
        res = json.loads(adapter.exportSnapshot(str(db_file), "Admin"))
        assert res["ok"] is False
        assert "active" in res["error"].lower()

        # Symlink target pointing to another file is rejected
        symlink_snap = tmp_path / "link_snap.sqlite"
        symlink_snap.symlink_to(db_file)
        res_link = json.loads(adapter.exportSnapshot(str(symlink_snap), "Admin"))
        assert res_link["ok"] is False

        # Disallowed output extension
        res_ext = json.loads(adapter.exportSnapshot(str(tmp_path / "evil.sh"), "Admin"))
        assert res_ext["ok"] is False

        # Input slots reject bad extensions, directories, missing files, symlinks, and active DB
        bad_xlsx = tmp_path / "not_excel.txt"
        bad_xlsx.write_text("hello", encoding="utf-8")
        assert json.loads(adapter.importXlsx(str(bad_xlsx), False, "Admin"))["ok"] is False
        assert json.loads(adapter.previewXlsxDiff(str(tmp_path)))["ok"] is False
        assert json.loads(adapter.applyXlsxDiff(str(db_file), 2568, 1, "Admin"))["ok"] is False

        xlsx_link = tmp_path / "link.xlsx"
        xlsx_link.symlink_to(bad_xlsx)
        assert json.loads(adapter.importXlsx(str(xlsx_link), False, "Admin"))["ok"] is False
    finally:
        conn.close()


def test_student_adapter_empty_export_uses_safe_writable_dir(tmp_path, monkeypatch):
    import apps.student_management_app.adapters.student_admin_adapter as saa

    docs_dir = tmp_path / "Docs"
    docs_dir.mkdir()
    monkeypatch.setattr(saa, "get_default_documents_dir", lambda: docs_dir)

    db_file = tmp_path / "student.sqlite"
    conn = _open_migrated_file_db(db_file)
    try:
        adapter = StudentAdminAdapter(conn)
        res = json.loads(adapter.exportSnapshot("", "Admin"))
        assert res["ok"] is True
        out_path = Path(res["data"]["output_path"])
        assert out_path == docs_dir / "snapshot.sqlite"
        assert out_path.is_file()
    finally:
        conn.close()


def test_librarian_adapter_path_validation_and_secure_pdf_export(tmp_path, monkeypatch):
    db_file = tmp_path / "library_live.sqlite"
    conn = _open_migrated_file_db(db_file)
    created_temp_pdf = None
    try:
        adapter = LibrarianAdminAdapter(conn)

        # Rejects active DB overwrite / bad extensions / symlinks for sync & roster
        assert json.loads(adapter.previewSync(str(db_file)))["ok"] is False
        assert json.loads(adapter.applySync(str(db_file)))["ok"] is False
        assert json.loads(adapter.importRoster(str(db_file), "Librarian"))["ok"] is False

        bad_file = tmp_path / "payload.sh"
        bad_file.write_text("#!/bin/sh\necho pwn", encoding="utf-8")
        assert json.loads(adapter.importRoster(str(bad_file), "Librarian"))["ok"] is False
        assert json.loads(adapter.exportLabelsPdf(json.dumps(["SMTE-00001-01"]), str(bad_file)))["ok"] is False

        # Empty output_path creates a random 0o600 temp PDF (never predictable /tmp/library_*_<ts>.pdf)
        pdf_res = json.loads(adapter.exportLabelsPdf(json.dumps(["SMTE-00001-01"]), ""))
        assert pdf_res["ok"] is True
        created_temp_pdf = Path(pdf_res["data"]["output_path"])
        assert created_temp_pdf.is_file()
        assert created_temp_pdf.suffix == ".pdf"
        assert created_temp_pdf.name.startswith("library_labels_")
        assert created_temp_pdf.read_bytes().startswith(b"%PDF-")
        if os.name == "posix":
            assert stat.S_IMODE(created_temp_pdf.stat().st_mode) == 0o600

        # Failed export with empty barcodes cleans up temp file instead of leaking 0-byte file
        before_msg = json.loads(adapter.exportLabelsPdf("[]", ""))
        assert before_msg["ok"] is False

        # openLocalFile rejects non-PDF, symlinks, and remote URLs; accepts real PDF via QUrl.fromLocalFile
        opened_urls = []
        from PySide6.QtGui import QDesktopServices
        monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened_urls.append(url) or True)

        assert adapter.openLocalFile(str(bad_file)) is False
        assert adapter.openLocalFile("https://example.com/evil.pdf") is False
        pdf_link = tmp_path / "sym.pdf"
        pdf_link.symlink_to(created_temp_pdf)
        assert adapter.openLocalFile(str(pdf_link)) is False

        assert adapter.openLocalFile(str(created_temp_pdf)) is True
        assert len(opened_urls) == 1
        assert opened_urls[0].isLocalFile()
        assert os.path.realpath(opened_urls[0].toLocalFile()) == os.path.realpath(str(created_temp_pdf))
    finally:
        conn.close()
        if created_temp_pdf and created_temp_pdf.exists():
            created_temp_pdf.unlink()


def test_qml_avoids_predictable_tmp_and_substring_url_parsing():
    cat_qml = Path("apps/librarian_management_app/qml/views/CategoryManagementView.qml").read_text(encoding="utf-8")
    book_dlg_qml = Path("apps/librarian_management_app/qml/dialogs/BookActionDialogs.qml").read_text(encoding="utf-8")
    lib_main_qml = Path("apps/librarian_management_app/qml/Main.qml").read_text(encoding="utf-8")
    stu_main_qml = Path("apps/student_management_app/qml/Main.qml").read_text(encoding="utf-8")
    sync_view_qml = Path("apps/student_management_app/qml/views/LineSyncExportView.qml").read_text(encoding="utf-8")

    assert "/tmp/library_" not in cat_qml
    assert "Qt.openUrlExternally" not in cat_qml
    assert "librarianAdmin.openLocalFile" in cat_qml
    assert "/tmp/library_labels_" not in book_dlg_qml
    assert "substring(7)" not in lib_main_qml
    assert "substring(7)" not in stu_main_qml
    assert '"snapshot.sqlite"' not in sync_view_qml


def test_booth_adapter_discovery_forwards_token_and_handles_legacy_mocks(tmp_path, monkeypatch):
    seen_calls = []

    def token_aware_discover(timeout=1.5, token=""):
        seen_calls.append({"timeout": timeout, "token": token})
        return None

    client = BoothLanClient(host="127.0.0.1", port=DEFAULT_LAN_PORT, token="sec-token-123")
    adapter = BoothAdapter(client=client, config_path=str(tmp_path / "booth.json"), auto_discover=True)
    try:
        monkeypatch.setattr(
            "apps.booth_app.adapters.booth_adapter.discover_librarian",
            token_aware_discover,
        )
        res = json.loads(adapter.discoverServer())
        assert res["ok"] is False
        assert seen_calls == [{"timeout": 1.5, "token": "sec-token-123"}]

        # Legacy 0-arg mock must still work without TypeError
        monkeypatch.setattr(
            "apps.booth_app.adapters.booth_adapter.discover_librarian",
            lambda: {"host": "127.0.0.1", "port": 8765, "version": "1.0.0"},
        )
        res_legacy = json.loads(adapter.discoverServer())
        assert res_legacy == {"ok": True, "host": "127.0.0.1", "port": 8765}

        # _try_rediscover passes token when supported and verifies live server
        conn = _open_migrated_file_db(tmp_path / "lib.sqlite")
        server = BoothLanServer(conn, host="127.0.0.1", port=0, token="sec-token-123")
        server.start()
        try:
            seen_rediscover = []

            def fake_auth_discover(timeout=0.4, token=""):
                seen_rediscover.append((timeout, token))
                return {"host": "127.0.0.1", "port": server.port, "version": "1.0"}

            adapter.client = BoothLanClient(host="127.0.0.1", port=1, token="sec-token-123")
            monkeypatch.setattr(
                "apps.booth_app.adapters.booth_adapter.discover_librarian",
                fake_auth_discover,
            )
            status = json.loads(adapter.getConnectionStatus())
            assert status["connected"] is True
            assert seen_rediscover == [(0.4, "sec-token-123")]
        finally:
            server.stop()
            conn.close()
    finally:
        adapter.close()
