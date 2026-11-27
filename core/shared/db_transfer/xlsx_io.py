"""Atomic XLSX workbook writer and bounded read-only reader for DB transfer."""

import os
import tempfile
import zipfile
from typing import Any, Sequence

from core.shared.mock_qt import normalize_file_path
from core.shared.result import Err, Ok, Result

_MAX_WORKBOOK_XML_BYTES = 10 * 1024 * 1024
_MAX_ROWS_PER_SHEET = 100_000


def write_xlsx_bundle(
    output_path: str,
    sheets: Sequence[tuple[str, Sequence[str], Sequence[Sequence[Any]]]],
) -> Result[str, str]:
    """Atomically write named sheets with headers and rows to an .xlsx workbook."""
    import openpyxl

    clean = normalize_file_path(output_path)
    if not clean or "\x00" in clean or os.path.islink(clean) or os.path.isdir(clean):
        return Err("Invalid XLSX output path")
    abs_path = os.path.abspath(clean)
    parent = os.path.dirname(abs_path)
    if not os.path.isdir(parent):
        return Err(f"Destination directory does not exist: {parent}")

    tmp_path = ""
    try:
        fd, tmp_path = tempfile.mkstemp(dir=parent, prefix=".tmp_bundle_", suffix=".xlsx")
        os.close(fd)
        wb = openpyxl.Workbook(write_only=True)
        for sheet_name, headers, rows in sheets:
            ws = wb.create_sheet(title=str(sheet_name)[:31])
            ws.append(list(headers))
            for row in rows:
                ws.append(list(row))
        wb.save(tmp_path)
        wb.close()
        os.replace(tmp_path, abs_path)
        return Ok(abs_path)
    except Exception as exc:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        return Err(f"Failed to write XLSX bundle: {exc}")


def _check_xlsx_zip_bounds(abs_path: str) -> Result[None, str]:
    try:
        with zipfile.ZipFile(abs_path, "r") as z:
            if "xl/workbook.xml" in z.namelist():
                if z.getinfo("xl/workbook.xml").file_size > _MAX_WORKBOOK_XML_BYTES:
                    return Err("XLSX workbook.xml exceeds 10 MB limit")
        return Ok(None)
    except Exception as exc:
        return Err(f"Invalid XLSX archive: {exc}")


def _read_sheet_dicts(ws: Any, max_rows: int) -> list[dict[str, Any]]:
    row_iter = ws.iter_rows(values_only=True)
    header_raw = next(row_iter, None)
    if not header_raw:
        return []
    headers = [str(h).strip() if h is not None else "" for h in header_raw]
    records: list[dict[str, Any]] = []
    for idx, row in enumerate(row_iter, start=1):
        if idx > max_rows:
            raise ValueError(f"Sheet '{ws.title}' exceeds {max_rows} row limit")
        if not any(cell is not None and str(cell).strip() != "" for cell in row):
            continue
        item = {headers[i]: (row[i] if i < len(row) else None) for i in range(len(headers)) if headers[i]}
        records.append(item)
    return records


def read_xlsx_bundle(
    input_path: str,
    required_sheets: Sequence[str],
    max_rows_per_sheet: int = _MAX_ROWS_PER_SHEET,
) -> Result[dict[str, list[dict[str, Any]]], str]:
    """Read and validate an XLSX bundle via streaming read-only openpyxl."""
    import openpyxl

    clean = normalize_file_path(input_path)
    if not clean or "\x00" in clean or os.path.islink(clean) or not os.path.isfile(clean):
        return Err(f"XLSX bundle file not found: {clean}")
    abs_path = os.path.abspath(clean)
    bound_res = _check_xlsx_zip_bounds(abs_path)
    if bound_res.is_err():
        return Err(bound_res.error or "Invalid XLSX file")

    wb = None
    try:
        wb = openpyxl.load_workbook(abs_path, read_only=True, data_only=True)
        missing = [s for s in required_sheets if s not in wb.sheetnames]
        if missing:
            return Err(f"XLSX bundle missing required sheet(s): {', '.join(missing)}")
        data = {name: _read_sheet_dicts(wb[name], max_rows_per_sheet) for name in wb.sheetnames}
        return Ok(data)
    except Exception as exc:
        return Err(f"Failed to read XLSX bundle: {exc}")
    finally:
        if wb is not None:
            wb.close()
