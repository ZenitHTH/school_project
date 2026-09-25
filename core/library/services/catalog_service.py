import sqlite3
from typing import Any, Dict, List, Optional
from core.shared.result import Result
from data.repositories import book_repo

BARCODE_PREFIX = "SMTE"


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

    def rename_category(self, category_id: int, new_name: str) -> Result:
        """Rename category with non-empty validation."""
        if not new_name or not new_name.strip():
            return Result.fail("Category name cannot be empty")
        try:
            book_repo.rename_category(self.conn, category_id, new_name.strip())
            return Result.success({"category_id": category_id, "name": new_name.strip()})
        except Exception as e:
            return Result.fail(f"Failed to rename category: {e}")

    def get_books_in_category(self, category_id: int) -> Result:
        """Fetch books assigned to category."""
        try:
            rows = book_repo.get_books_by_category(self.conn, category_id)
            return Result.success([dict(r) for r in rows])
        except Exception as e:
            return Result.fail(f"Failed to fetch books in category: {e}")

    def delete_category(self, category_id: int, reassign_to_id: Optional[int] = None) -> Result:
        """Delete category with optional book reassignment."""
        try:
            book_repo.delete_category(self.conn, category_id, reassign_to_id)
            return Result.success({"deleted": category_id, "reassigned_to": reassign_to_id})
        except Exception as e:
            return Result.fail(f"Failed to delete category: {e}")

    def add_book(
        self,
        title: str,
        isbn: Optional[str] = None,
        author: Optional[str] = None,
        publisher: Optional[str] = None,
        category_id: Optional[int] = None,
        shelf_location: Optional[str] = None,
        barcodes: Optional[List[str]] = None,
        copy_count: int = 0,
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

            generated_barcodes = []
            if copy_count > 0:
                for seq in range(1, copy_count + 1):
                    generated_barcodes.append(f"{BARCODE_PREFIX}-{book_id:05d}-{seq:02d}")
            elif barcodes:
                generated_barcodes = [b.strip() for b in barcodes if b.strip()]

            copy_ids = []
            if generated_barcodes:
                copy_ids = book_repo.add_copies(self.conn, book_id=book_id, barcodes=generated_barcodes, actor=actor)

            return Result.success({
                "book_id": book_id,
                "copy_ids": copy_ids,
                "barcodes": generated_barcodes,
            })
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

    def add_copies(
        self,
        book_id: int,
        barcodes: Optional[List[str]] = None,
        additional_count: int = 0,
        actor: Optional[str] = None,
    ) -> Result:
        """Add physical copy barcodes (auto-generated by count or explicit list)."""
        target_barcodes = []
        if additional_count > 0:
            existing = book_repo.count_copies_ever(self.conn, book_id)
            for seq in range(existing + 1, existing + additional_count + 1):
                target_barcodes.append(f"{BARCODE_PREFIX}-{book_id:05d}-{seq:02d}")
        elif barcodes:
            target_barcodes = [b.strip() for b in barcodes if b.strip()]

        if not target_barcodes:
            return Result.fail("No valid barcodes or copy count provided")
        try:
            copy_ids = book_repo.add_copies(self.conn, book_id=book_id, barcodes=target_barcodes, actor=actor)
            return Result.success({
                "book_id": book_id,
                "copy_ids": copy_ids,
                "barcodes": target_barcodes,
            })
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
        """Change copy status ('available', 'on_loan', 'lost', 'damaged', 'retired', 'disposed')."""
        valid_statuses = {"available", "on_loan", "lost", "damaged", "retired", "disposed"}
        if status not in valid_statuses:
            return Result.fail(f"Invalid copy status '{status}'")
        if status == "disposed" and (not reason or not reason.strip()):
            return Result.fail("Disposed status requires a documented reason")
        try:
            clean_reason = reason.strip() if reason else None
            book_repo.mark_copy(self.conn, copy_id=copy_id, new_status=status, reason=clean_reason, actor=actor)
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
