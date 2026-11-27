"""Canonical JSON manifest and SHA-256 checksum utilities for DB bundles."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from core.shared.result import Err, Ok, Result


def compute_tables_checksum(tables: Mapping[str, Sequence[Sequence[Any]]]) -> str:
    """Compute deterministic SHA-256 hex digest over sorted table rows."""
    canonical = {
        str(name): [list(row) for row in rows]
        for name, rows in sorted(tables.items(), key=lambda kv: str(kv[0]))
    }
    payload = json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_manifest(
    domain: str,
    schema_version: int,
    tables: Mapping[str, Sequence[Sequence[Any]]],
) -> dict[str, Any]:
    """Build transfer manifest dictionary with domain, version, row counts, and SHA-256."""
    return {
        "domain": str(domain),
        "schema_version": int(schema_version),
        "checksum": compute_tables_checksum(tables),
        "row_counts": {str(k): len(v) for k, v in sorted(tables.items(), key=lambda kv: str(kv[0]))},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def verify_manifest(
    manifest: Mapping[str, Any],
    expected_domain: str,
    tables: Mapping[str, Sequence[Sequence[Any]]],
) -> Result[dict[str, Any], str]:
    """Verify bundle domain and SHA-256 checksum match extracted table rows."""
    actual_domain = manifest.get("domain")
    if actual_domain != expected_domain:
        return Err(f"Wrong bundle domain: expected '{expected_domain}', got '{actual_domain}'")
    expected_hash = manifest.get("checksum")
    actual_hash = compute_tables_checksum(tables)
    if not isinstance(expected_hash, str) or expected_hash != actual_hash:
        return Err("Checksum verification failed: bundle data has been tampered or corrupted")
    return Ok(dict(manifest))
