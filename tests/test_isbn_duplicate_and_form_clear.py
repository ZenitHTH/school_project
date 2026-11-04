"""
tests/test_isbn_duplicate_and_form_clear.py
Covers:
  - CatalogService.get_active_book_by_isbn (exact, normalized, case-insensitive, retired, missing)
  - LibrarianAdminAdapter.checkBookByIsbn (JSON responses, exists flag, sanitization, case-insensitivity)
"""
import json
import pytest

from data.db import get_connection
from data.migrate import apply_migrations
from core.library.services.catalog_service import CatalogService
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter


@pytest.fixture
def catalog_env(tmp_path):
    conn = get_connection(str(tmp_path / "catalog_test.sqlite"), pin="123456")
    apply_migrations(conn)
    svc = CatalogService(conn)
    yield svc, conn
    conn.close()


@pytest.fixture
def adapter_env(tmp_path):
    conn = get_connection(str(tmp_path / "adapter_test.sqlite"), pin="123456")
    apply_migrations(conn)
    adapter = LibrarianAdminAdapter(conn)
    yield adapter, conn
    conn.close()


# ---------------------------------------------------------------------------
# 1. Catalog Service Tests
# ---------------------------------------------------------------------------

def test_catalog_service_lookup_active_book_by_isbn_exact_and_variants(catalog_env):
    svc, _ = catalog_env
    res = svc.add_book(title="วิทยาการคำนวณ", isbn="978-616-00-1234-5", copy_count=2)
    assert res.ok is True

    r1 = svc.get_active_book_by_isbn("978-616-00-1234-5")
    assert r1.ok is True and r1.data is not None and r1.data["title"] == "วิทยาการคำนวณ"

    r2 = svc.get_active_book_by_isbn("9786160012345")
    assert r2.ok is True and r2.data is not None and r2.data["book_id"] == r1.data["book_id"]

    r3 = svc.get_active_book_by_isbn("978 616 00 1234 5")
    assert r3.ok is True and r3.data is not None


def test_catalog_service_lookup_isbn10_case_insensitive(catalog_env):
    svc, _ = catalog_env
    # Add with uppercase 'X'
    res = svc.add_book(title="วรรณคดีไทย", isbn="0-8044-2957-X", copy_count=1)
    assert res.ok is True

    # Search with lowercase 'x' and without hyphens
    rx = svc.get_active_book_by_isbn("080442957x")
    assert rx.ok is True and rx.data is not None
    assert rx.data["title"] == "วรรณคดีไทย"

    # Search with uppercase 'X'
    r_cap = svc.get_active_book_by_isbn("080442957X")
    assert r_cap.ok is True and r_cap.data is not None


def test_catalog_service_lookup_missing_and_empty_isbn(catalog_env):
    svc, _ = catalog_env
    assert svc.get_active_book_by_isbn("9789999999999").data is None
    assert svc.get_active_book_by_isbn("").data is None
    assert svc.get_active_book_by_isbn("   ").data is None


def test_catalog_service_lookup_ignores_retired_book(catalog_env):
    svc, _ = catalog_env
    res = svc.add_book(title="หนังสือเก่า", isbn="978-616-99-9999-9", copy_count=1)
    book_id = res.data["book_id"]
    assert svc.get_active_book_by_isbn("978-616-99-9999-9").data is not None

    svc.retire_book(book_id)
    found_after = svc.get_active_book_by_isbn("978-616-99-9999-9")
    assert found_after.ok is True and found_after.data is None


# ---------------------------------------------------------------------------
# 2. Librarian Admin Adapter Tests
# ---------------------------------------------------------------------------

def test_librarian_adapter_check_book_by_isbn_exists_and_missing(adapter_env):
    adapter, _ = adapter_env
    res = json.loads(adapter.checkBookByIsbn("978-616-12-3456-7"))
    assert res["ok"] is True and res["exists"] is False and res["book"] is None

    adapter.addBook("เคมีเบื้องต้น", "978-616-12-3456-7", "อ.เคมี")
    res2 = json.loads(adapter.checkBookByIsbn("978-616-12-3456-7"))
    assert res2["ok"] is True and res2["exists"] is True
    assert res2["book"]["title"] == "เคมีเบื้องต้น"
    assert "total_copies" in res2["book"]


def test_librarian_adapter_check_book_by_isbn10_case_insensitive(adapter_env):
    adapter, _ = adapter_env
    adapter.addBook("ประวัติศาสตร์", "0-19-852663-x")
    res = json.loads(adapter.checkBookByIsbn("019852663X"))
    assert res["ok"] is True and res["exists"] is True
    assert res["book"]["title"] == "ประวัติศาสตร์"
