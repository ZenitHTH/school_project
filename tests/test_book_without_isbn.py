"""
tests/test_book_without_isbn.py
Contract tests for books without ISBN: an empty ISBN must insert, update,
search, and lend without error. The DB stores NULL (never a sentinel),
and the adapter JSON exposes it as '' for QML role stability.
"""
import json
import re

import pytest

from data.db import get_connection
from data.migrate import apply_migrations
from core.library.services.catalog_service import CatalogService
from apps.librarian_management_app.adapters.librarian_admin_adapter import LibrarianAdminAdapter


@pytest.fixture
def librarian(tmp_path):
    conn = get_connection(str(tmp_path / 'library.sqlite'), pin='123456')
    apply_migrations(conn)
    adapter = LibrarianAdminAdapter(conn)
    yield adapter, conn
    conn.close()


def test_add_book_empty_isbn_stores_null(librarian):
    _, conn = librarian
    svc = CatalogService(conn)
    res = svc.add_book(title='หนังสือไม่มี ISBN', isbn='', copy_count=1)
    assert res.is_ok()
    row = conn.execute(
        'SELECT isbn FROM books WHERE title = ?', ('หนังสือไม่มี ISBN',)
    ).fetchone()
    assert row['isbn'] is None
    book_id = conn.execute(
        'SELECT book_id FROM books WHERE title = ?', ('หนังสือไม่มี ISBN',)
    ).fetchone()[0]
    copies = conn.execute(
        'SELECT barcode FROM book_copies WHERE book_id = ?', (book_id,)
    ).fetchall()
    assert len(copies) == 1
    assert re.fullmatch(r'SMTE-\d{5}-\d{2}', copies[0]['barcode'])


def test_two_null_isbn_books_coexist(librarian):
    adapter, conn = librarian
    svc = CatalogService(conn)
    r1 = svc.add_book(title='A ไม่มี ISBN', isbn=None, copy_count=1)
    r2 = svc.add_book(title='B ไม่มี ISBN', isbn=None, copy_count=1)
    assert r1.is_ok()
    assert r2.is_ok()
    check = json.loads(adapter.checkBookByIsbn(''))
    assert check['ok'] is True
    assert check['exists'] is False


def test_null_isbn_roundtrip_adapter_json(librarian):
    adapter, _ = librarian
    add_res = json.loads(
        adapter.addBook('หนังสือไม่มี ISBN 2', '', '', '', '', '', 'NOISBN-01')
    )
    assert add_res['ok'] is True
    book_id = add_res['data']['book_id']
    book = json.loads(adapter.getBook(book_id))
    assert book['isbn'] == ''
    hits = json.loads(adapter.searchBooks('หนังสือไม่มี ISBN 2'))
    assert any(b['book_id'] == book_id for b in hits)
    assert hits[0]['isbn'] == ''


def test_update_book_empty_isbn_stays_null(librarian):
    adapter, conn = librarian
    add_res = json.loads(
        adapter.addBook('ISBN เดิม', '9786100000001', '', '', '', '', 'OLD-01')
    )
    assert add_res['ok'] is True
    book_id = add_res['data']['book_id']
    up = json.loads(
        adapter.updateBook(
            book_id=book_id,
            title='ISBN เดิม',
            isbn='',
            author='',
            category_id_str='',
            shelf_location='',
        )
    )
    assert up['ok'] is True
    row = conn.execute(
        'SELECT isbn FROM books WHERE book_id = ?', (book_id,)
    ).fetchone()
    assert row['isbn'] is None
