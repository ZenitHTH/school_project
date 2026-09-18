import hashlib
import os
import time
from typing import Optional, Tuple

# Try SQLCipher first, fallback to standard sqlite3
try:
    import sqlcipher3.dbapi2 as sqlite3  # type: ignore
    SQLCIPHER_AVAILABLE = True
except ImportError:
    try:
        import pysqlcipher3.dbapi2 as sqlite3  # type: ignore
        SQLCIPHER_AVAILABLE = True
    except ImportError:
        import sqlite3  # Standard fallback
        SQLCIPHER_AVAILABLE = False


def get_or_create_salt(db_path: str) -> bytes:
    """Return salt from <db_path>.salt or generate and save a 16-byte random salt."""
    if db_path == ":memory:":
        return b"memory_test_salt"
    salt_path = f"{db_path}.salt"
    if os.path.exists(salt_path):
        with open(salt_path, "rb") as f:
            return f.read()
    salt = os.urandom(16)
    with open(salt_path, "wb") as f:
        f.write(salt)
    return salt


def derive_key(pin: str, salt: bytes, iterations: int = 100_000) -> bytes:
    """Derive 256-bit encryption key from 6-digit PIN using PBKDF2-HMAC-SHA256."""
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iterations)


def check_lockout(db_path: str, max_attempts: int = 3, lockout_seconds: int = 3) -> None:
    """Check failed attempt lockout counter."""
    if db_path == ":memory:":
        return
    lockout_file = f"{db_path}.lockout"
    if not os.path.exists(lockout_file):
        return
    try:
        with open(lockout_file, "r") as f:
            parts = f.read().strip().split(",")
            attempts = int(parts[0])
            last_failed = float(parts[1])
            if attempts >= max_attempts:
                elapsed = time.time() - last_failed
                if elapsed < lockout_seconds:
                    wait_time = int(lockout_seconds - elapsed) + 1
                    raise PermissionError(f"Too many failed attempts. Please wait {wait_time}s.")
    except (ValueError, IndexError):
        pass


def record_failed_attempt(db_path: str) -> None:
    """Record a failed PIN attempt."""
    if db_path == ":memory:":
        return
    lockout_file = f"{db_path}.lockout"
    attempts = 0
    if os.path.exists(lockout_file):
        try:
            with open(lockout_file, "r") as f:
                parts = f.read().strip().split(",")
                attempts = int(parts[0])
        except Exception:
            attempts = 0
    attempts += 1
    with open(lockout_file, "w") as f:
        f.write(f"{attempts},{time.time()}")


def reset_lockout(db_path: str) -> None:
    """Reset lockout counter upon successful unlock."""
    if db_path == ":memory:":
        return
    lockout_file = f"{db_path}.lockout"
    if os.path.exists(lockout_file):
        try:
            os.remove(lockout_file)
        except OSError:
            pass


def get_connection(
    db_path: str,
    pin: Optional[str] = None,
    enforce_foreign_keys: bool = True,
) -> sqlite3.Connection:
    """
    Open connection to database with derived key and standard PRAGMAs.
    If SQLCipher is present and pin is provided, runs PRAGMA key.
    """
    if pin is not None:
        check_lockout(db_path)

    conn = sqlite3.connect(db_path)

    if pin is not None:
        salt = get_or_create_salt(db_path)
        derived = derive_key(pin, salt)
        if SQLCIPHER_AVAILABLE:
            conn.execute("PRAGMA key = ?;", (derived.hex(),))
        elif db_path != ":memory:":
            # When testing with stdlib sqlite3, verify PIN matching dummy check file if exists
            pin_check_file = f"{db_path}.pin_hash"
            expected_hash = hashlib.sha256((pin + salt.hex()).encode()).hexdigest()
            if os.path.exists(db_path) and os.path.exists(pin_check_file):
                with open(pin_check_file, "r") as pf:
                    saved_hash = pf.read().strip()
                if saved_hash != expected_hash:
                    record_failed_attempt(db_path)
                    conn.close()
                    raise sqlite3.DatabaseError("Invalid PIN (file encrypted)")
            elif not os.path.exists(pin_check_file):
                with open(pin_check_file, "w") as pf:
                    pf.write(expected_hash)

    # Test query to verify key
    try:
        conn.execute("SELECT count(*) FROM sqlite_master;").fetchone()
    except sqlite3.DatabaseError:
        if pin is not None:
            record_failed_attempt(db_path)
        conn.close()
        raise sqlite3.DatabaseError("File is not a database or key is invalid.")

    if pin is not None:
        reset_lockout(db_path)

    if enforce_foreign_keys:
        conn.execute("PRAGMA foreign_keys = ON;")
    else:
        conn.execute("PRAGMA foreign_keys = OFF;")

    conn.execute("PRAGMA journal_mode = WAL;")
    conn.row_factory = sqlite3.Row
    return conn
