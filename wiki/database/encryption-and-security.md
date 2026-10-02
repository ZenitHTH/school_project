# Encryption & Security Architecture (`data/db.py`)

## 1. Overview
The database layer enforces application-level security and optional transparent database-at-rest encryption via SQLCipher, paired with PBKDF2 PIN derivation and lockout protection.

---

## 2. Key Derivation & PIN Hashing
When initialized with PIN authentication:
- **PIN format**: 6-digit numeric PIN (`^\d{6}$`).
- **Salt generation**: Unique 16-byte cryptographically secure random salt generated via `os.urandom(16)` and stored alongside the database as `<db_path>.salt`.
- **PBKDF2 Derivation**:
  - Algorithm: `hashlib.pbkdf2_hmac("sha256", pin, salt, iterations=100_000)`
  - Output: 256-bit encryption key.
  - Converted to hex string formatted for `PRAGMA key = "x'<hex_key>'"` under SQLCipher.

---

## 3. Brute Force Protection (Lockout Mechanism)
To prevent local offline or UI brute force attacks:
- **Lockout Tracking**: Recorded in `<db_path>.lockout` as `<failed_attempts>,<last_timestamp>`.
- **Threshold**: 3 consecutive failed attempts triggers a mandatory wait period (default: 3 seconds exponential lockout).
- **Reset**: Successful authentication clears the lockout state via `clear_lockout(db_path)`.

---

## 4. SQLCipher Fallback & Compatibility
In environments where native `sqlcipher3` or `pysqlcipher3` C-extensions cannot be bundled:
1. Dynamically detects `SQLCIPHER_AVAILABLE`.
2. If unavailable, falls back gracefully to Python standard library `sqlite3` without throwing missing wheel import errors.
3. In-memory databases (`:memory:`) use deterministic mock salts (`b"memory_test_salt"`) for test suite isolation.
