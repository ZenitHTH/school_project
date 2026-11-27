"""Tests for core.shared.db_transfer (manifest, hardened sqlite_io, backup, xlsx_io)."""

import os
import sqlite3

from core.shared.db_transfer.backup import create_pre_import_backup
from core.shared.db_transfer.manifest import build_manifest, compute_tables_checksum, verify_manifest
from core.shared.db_transfer.sqlite_io import read_sqlite_bundle, write_sqlite_bundle
from core.shared.db_transfer.xlsx_io import read_xlsx_bundle, write_xlsx_bundle


def test_sqlite_bundle_roundtrip_and_checksum_verification(tmp_path):
    out = tmp_path / "books_bundle.sqlite"
    schemas = {"categories": "CREATE TABLE categories (category_id INTEGER PRIMARY KEY, name TEXT NOT NULL)"}
    rows = {"categories": [(1, "วิทยาศาสตร์")]}
    manifest = build_manifest("books", schema_version=1, tables=rows)

    res = write_sqlite_bundle(str(out), manifest, schemas, rows)
    assert res.is_ok()

    read_res = read_sqlite_bundle(str(out), expected_domain="books", required_tables=["categories"])
    assert read_res.is_ok()
    meta, loaded = read_res.unwrap()
    assert meta["domain"] == "books"
    assert loaded["categories"] == [{"category_id": 1, "name": "วิทยาศาสตร์"}]


def test_read_sqlite_bundle_rejects_wrong_domain_tamper_and_views(tmp_path):
    bad = tmp_path / "malicious.sqlite"
    conn = sqlite3.connect(bad)
    conn.execute("CREATE TABLE transfer_manifest (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute(
        "CREATE VIEW categories AS WITH RECURSIVE r(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM r) SELECT x FROM r"
    )
    conn.commit()
    conn.close()

    assert read_sqlite_bundle(str(bad), expected_domain="books", required_tables=["categories"]).is_err()

    # Reject triggers too
    trig = tmp_path / "trig.sqlite"
    schemas = {"categories": "CREATE TABLE categories (category_id INTEGER PRIMARY KEY, name TEXT NOT NULL)"}
    rows = {"categories": [(1, "ศิลปะ")]}
    write_sqlite_bundle(str(trig), build_manifest("books", 1, rows), schemas, rows)
    tc = sqlite3.connect(trig)
    tc.execute("CREATE TRIGGER evil_t AFTER INSERT ON categories BEGIN SELECT 1; END;")
    tc.commit()
    tc.close()
    assert read_sqlite_bundle(str(trig), expected_domain="books", required_tables=["categories"]).is_err()

    # Tampered row fails SHA-256 verification; wrong domain rejected
    good = tmp_path / "tampered.sqlite"
    write_sqlite_bundle(str(good), build_manifest("books", 1, rows), schemas, rows)
    assert read_sqlite_bundle(str(good), expected_domain="students", required_tables=["categories"]).is_err()

    c = sqlite3.connect(good)
    c.execute("UPDATE categories SET name = 'Tampered'")
    c.commit()
    c.close()
    assert read_sqlite_bundle(str(good), expected_domain="books", required_tables=["categories"]).is_err()


def test_create_pre_import_backup_writes_valid_copy(tmp_path):
    db_file = tmp_path / "live.sqlite"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO t VALUES (42)")
    conn.commit()

    res = create_pre_import_backup(conn, str(db_file))
    assert res.is_ok()
    assert os.path.exists(res.unwrap())
    backup_conn = sqlite3.connect(res.unwrap())
    assert backup_conn.execute("SELECT id FROM t").fetchall() == [(42,)]
    backup_conn.close()
    conn.close()


def test_xlsx_bundle_roundtrip_and_missing_sheet_rejection(tmp_path):
    out = tmp_path / "bundle.xlsx"
    sheets = [
        ("categories", ["category_id", "name"], [(1, "ภาษาไทย"), (2, None)]),
        ("books", ["book_id", "title", "isbn"], [(1, "วรรณคดีไทย", "978-616-0001")]),
    ]
    w_res = write_xlsx_bundle(str(out), sheets)
    assert w_res.is_ok()

    r_res = read_xlsx_bundle(str(out), required_sheets=["categories", "books"])
    assert r_res.is_ok()
    data = r_res.unwrap()
    assert data["categories"][0] == {"category_id": 1, "name": "ภาษาไทย"}
    assert data["categories"][1] == {"category_id": 2, "name": None}
    assert data["books"][0]["title"] == "วรรณคดีไทย"

    bad_res = read_xlsx_bundle(str(out), required_sheets=["categories", "missing_sheet"])
    assert bad_res.is_err()


def test_manifest_checksum_is_order_independent_for_table_keys():
    a = compute_tables_checksum({"b": [(1, "x")], "a": [(2, "y")]})
    b = compute_tables_checksum({"a": [[2, "y"]], "b": [[1, "x"]]})
    assert a == b
    m = build_manifest("books", 10, {"a": [(1,)]})
    assert verify_manifest(m, "books", {"a": [(1,)]}).is_ok()
    assert verify_manifest(m, "students", {"a": [(1,)]}).is_err()
