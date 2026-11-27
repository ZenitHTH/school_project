"""Hardened atomic SQLite bundle writer and read-only inspector."""

import json
import os
import re
import sqlite3
import tempfile
from typing import Any, Mapping, Sequence
from urllib.parse import quote

from core.shared.db_transfer.manifest import verify_manifest
from core.shared.mock_qt import normalize_file_path
from core.shared.result import Err, Ok, Result

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MANIFEST_DDL = "CREATE TABLE transfer_manifest (key TEXT PRIMARY KEY, value TEXT NOT NULL)"


def _validate_identifier(name: str) -> str:
    if not _IDENT_RE.fullmatch(name):
        raise ValueError(f"Invalid SQLite table identifier: {name!r}")
    return name


def _validate_write_path(output_path: str) -> Result[str, str]:
    clean = normalize_file_path(output_path)
    if not clean or "\x00" in clean:
        return Err("Invalid output path")
    if os.path.islink(clean) or os.path.isdir(clean):
        return Err("Output path cannot be a directory or symlink")
    abs_path = os.path.abspath(clean)
    parent = os.path.dirname(abs_path)
    if not os.path.isdir(parent):
        return Err(f"Destination directory does not exist: {parent}")
    return Ok(abs_path)


def _validate_read_path(input_path: str) -> Result[str, str]:
    clean = normalize_file_path(input_path)
    if not clean or "\x00" in clean:
        return Err("Invalid input path")
    if os.path.islink(clean) or not os.path.isfile(clean):
        return Err(f"Bundle file not found: {clean}")
    return Ok(os.path.abspath(clean))


def _insert_table_rows(
    cur: sqlite3.Cursor, table: str, rows: Sequence[tuple[Any, ...]]
) -> None:
    if not rows:
        return
    width = len(rows[0])
    placeholders = ",".join("?" for _ in range(width))
    cur.executemany(f'INSERT INTO "{table}" VALUES ({placeholders})', rows)


def write_sqlite_bundle(
    output_path: str,
    manifest: Mapping[str, Any],
    schemas: Mapping[str, str],
    rows_by_table: Mapping[str, Sequence[tuple[Any, ...]]],
) -> Result[str, str]:
    """Atomically write manifest and domain tables to a standalone SQLite bundle."""
    path_res = _validate_write_path(output_path)
    if path_res.is_err():
        return path_res
    abs_path = path_res.unwrap()
    tmp_path = ""
    try:
        fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(abs_path), prefix=".tmp_bundle_", suffix=".sqlite")
        os.close(fd)
        conn = sqlite3.connect(tmp_path)
        try:
            with conn:
                cur = conn.cursor()
                cur.execute(_MANIFEST_DDL)
                cur.execute("INSERT INTO transfer_manifest VALUES ('manifest', ?)", (json.dumps(dict(manifest), ensure_ascii=False),))
                for tname, ddl in schemas.items():
                    safe_name = _validate_identifier(tname)
                    cur.execute(ddl)
                    _insert_table_rows(cur, safe_name, rows_by_table.get(tname, ()))
        finally:
            conn.close()
        os.replace(tmp_path, abs_path)
        return Ok(abs_path)
    except Exception as exc:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        return Err(f"Failed to write SQLite bundle: {exc}")


def _validate_bundle_schema(conn: sqlite3.Connection, required_tables: Sequence[str]) -> Result[None, str]:
    conn.execute("PRAGMA trusted_schema = OFF;")
    cur = conn.cursor()
    bad = cur.execute("SELECT name, type FROM sqlite_master WHERE type IN ('view', 'trigger')").fetchall()
    if bad:
        return Err(f"Unsafe SQLite bundle objects rejected: {bad[0]['name']} ({bad[0]['type']})")
    rows = cur.execute("SELECT name, type, sql FROM sqlite_master WHERE type = 'table'").fetchall()
    regular = set()
    for r in rows:
        if (r["sql"] or "").lstrip().upper().startswith("CREATE VIRTUAL TABLE"):
            return Err(f"Virtual table rejected in SQLite bundle: {r['name']}")
        regular.add(r["name"])
    needed = {"transfer_manifest", *required_tables}
    missing = [t for t in needed if t not in regular]
    return Err(f"Bundle missing required table(s): {', '.join(missing)}") if missing else Ok(None)


def _read_manifest_dict(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute("SELECT key, value FROM transfer_manifest").fetchall()
    mapping = {r["key"]: r["value"] for r in rows}
    if "manifest" in mapping:
        return dict(json.loads(mapping["manifest"]))
    return {k: json.loads(v) for k, v in mapping.items()}


def read_sqlite_bundle(
    input_path: str,
    expected_domain: str,
    required_tables: Sequence[str],
) -> Result[tuple[dict[str, Any], dict[str, list[dict[str, Any]]]], str]:
    """Read and checksum-verify an untrusted SQLite bundle under mode=ro."""
    path_res = _validate_read_path(input_path)
    if path_res.is_err():
        return Err(path_res.error or "Invalid bundle path")
    uri = f"file:{quote(path_res.unwrap())}?mode=ro"
    conn = None
    try:
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        schema_res = _validate_bundle_schema(conn, required_tables)
        if schema_res.is_err():
            return Err(schema_res.error or "Invalid bundle schema")
        manifest = _read_manifest_dict(conn)
        table_names = list(manifest.get("row_counts", {}).keys()) or list(required_tables)
        dict_rows: dict[str, list[dict[str, Any]]] = {}
        tuple_rows: dict[str, list[tuple[Any, ...]]] = {}
        for tname in table_names:
            safe_name = _validate_identifier(tname)
            fetched = conn.execute(f'SELECT * FROM "{safe_name}"').fetchall()
            dict_rows[safe_name] = [dict(r) for r in fetched]
            tuple_rows[safe_name] = [tuple(r) for r in fetched]
        ver_res = verify_manifest(manifest, expected_domain, tuple_rows)
        if ver_res.is_err():
            return Err(ver_res.error or "Checksum verification failed")
        return Ok((ver_res.unwrap(), dict_rows))
    except Exception as exc:
        return Err(f"Failed to read SQLite bundle: {exc}")
    finally:
        if conn is not None:
            conn.close()
