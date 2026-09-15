import sqlite3
from typing import Any, Dict, List, Optional
from core.shared.result import Result
from data.repositories import book_repo


class CatalogService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_categories(self) -> Result:
        """Fetch all categories."""
        try:
            rows = book_repo.list_categories(self.conn)
            return Result.success([dict(r) for r in rows])
        except Exception as e:
            return Result.fail(f"Failed to list categories: {e}")

    def add_category(self, name: str) -> Result:
        """Add new category if name is non-empty."""
        if not name or not name.strip():
            return Result.fail("Category name cannot be empty")
        try:
            cat_id = book_repo.add_category(self.conn, name.strip())
            return Result.success({"category_id": cat_id, "name": name.strip()})
        except Exception as e:
            return Result.fail(f"Failed to add category: {e}")

    def add_book(
        self,
        title: str,
        isbn: Optional[str] = None,
        author: Optional[str] = None,
        publisher: Optional[str] = None,
        category_id: Optional[int] = None,
        shelf_location: Optional[str] = None,
        barcodes: Optional[List[str]] = None,
        actor: Optional[str] = None,
    ) -> Result:
        """Add a book and optionally its physical copies."""
        if not title or not title.strip():
            return Result.fail("Book title cannot be empty")
        try:
            book_id = book_repo.add_book(
                self.conn,
                title=title.strip(),
                isbn=isbn.strip() if isbn else None,
                author=author.strip() if author else None,
                publisher=publisher.strip() if publisher else None,
                category_id=category_id,
                shelf_location=shelf_location.strip() if shelf_location else None,
                actor=actor,
            )

            copy_ids = []
            if barcodes:
                copy_ids = book_repo.add_copies(self.conn, book_id=book_id, barcodes=barcodes, actor=actor)

            return Result.success({"book_id": book_id, "copy_ids": copy_ids})
        except Exception as e:
            return Result.fail(f"Failed to add book: {e}")

    def update_book(
        self,
        book_id: int,
        title: str,
        isbn: Optional[str] = None,
        author: Optional[str] = None,
        publisher: Optional[str] = None,
        category_id: Optional[int] = None,
        shelf_location: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> Result:
        """Update book metadata."""
        if not title or not title.strip():
            return Result.fail("Book title cannot be empty")
        try:
            book_repo.update_book(
                self.conn,
                book_id=book_id,
                title=title.strip(),
                isbn=isbn.strip() if isbn else None,
                author=author.strip() if author else None,
                publisher=publisher.strip() if publisher else None,
                category_id=category_id,
                shelf_location=shelf_location.strip() if shelf_location else None,
                actor=actor,
            )
            return Result.success({"book_id": book_id})
        except Exception as e:
            return Result.fail(f"Failed to update book: {e}")

    def retire_book(self, book_id: int, actor: Optional[str] = None) -> Result:
        """Soft-delete book and retire all its copies."""
        try:
            book_repo.retire_book(self.conn, book_id=book_id, actor=actor)
            return Result.success({"book_id": book_id})
        except Exception as e:
            return Result.fail(f"Failed to retire book: {e}")

    def add_copies(self, book_id: int, barcodes: List[str], actor: Optional[str] = None) -> Result:
        """Add physical copy barcodes."""
        clean_barcodes = [b.strip() for b in barcodes if b.strip()]
        if not clean_barcodes:
            return Result.fail("No valid barcodes provided")
        try:
            copy_ids = book_repo.add_copies(self.conn, book_id=book_id, barcodes=clean_barcodes, actor=actor)
            return Result.success({"book_id": book_id, "copy_ids": copy_ids})
        except sqlite3.IntegrityError:
            return Result.fail("One or more barcodes already exist in the system")
        except Exception as e:
            return Result.fail(f"Failed to add copies: {e}")

    def mark_copy(
        self,
        copy_id: int,
        status: str,
        reason: Optional[str] = None,
        actor: Optional[str] = None,
    ) -> Result:
        """Change copy status ('available', 'lost', 'damaged', 'retired')."""
        valid_statuses = {"available", "on_loan", "lost", "damaged", "retired"}
        if status not in valid_statuses:
            return Result.fail(f"Invalid copy status '{status}'")
        try:
            book_repo.mark_copy(self.conn, copy_id=copy_id, new_status=status, reason=reason, actor=actor)
            return Result.success({"copy_id": copy_id, "status": status})
        except Exception as e:
            return Result.fail(f"Failed to mark copy: {e}")

    def get_book(self, book_id: int) -> Result:
        """Get book info with its list of physical copies."""
        try:
            b = book_repo.get_book(self.conn, book_id)
            if not b:
                return Result.fail(f"Book {book_id} not found")
            book_dict = dict(b)
            copies = book_repo.get_copies_for_book(self.conn, book_id)
            book_dict["copies"] = [dict(c) for c in copies]
            return Result.success(book_dict)
        except Exception as e:
            return Result.fail(f"Failed to fetch book: {e}")

    def search(
        self,
        query: str,
        category_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Result:
        """Search books with FTS5 and optional category filter."""
        try:
            rows = book_repo.search_books(
                self.conn,
                query=query,
                category_id=category_id,
                limit=limit,
                offset=offset,
            )
            return Result.success([dict(r) for r in rows])
        except Exception as e:
            return Result.fail(f"Catalog search failed: {e}")

    def get_copy_by_barcode(self, barcode: str) -> Result:
        """Lookup physical copy by its unique barcode."""
        try:
            row = book_repo.get_copy_by_barcode(self.conn, barcode)
            if not row:
                return Result.fail(f"Copy with barcode '{barcode}' not found")
            return Result.success(dict(row))
        except Exception as e:
            return Result.fail(f"Failed to lookup barcode: {e}")
