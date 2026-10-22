# Design and Evidence Report — Recipe Box API (user accounts)

Evidence run: 2026-10-22, Python 3.13, Flask 3.1.3, Werkzeug 3.1.9, fresh
`recipes.db` from `python init_db.py`, server started with `python app.py`
(listening on `127.0.0.1:5000`).

------------------------------------------------------------------------
## (1) Users table schema

Defined in `init_db.py` (commit `424372a`):

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
```

| Field | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PRIMARY KEY (rowid alias, auto-assigned) |
| `username` | TEXT | NOT NULL, UNIQUE |
| `email` | TEXT | NOT NULL, UNIQUE |
| `password_hash` | TEXT | NOT NULL |

- **Uniqueness constraints enforced:** two separate column-level `UNIQUE`
  constraints, one on `username` and one on `email`. `PRAGMA index_list(users)`
  on the created database shows both backing indexes
  (`sqlite_autoindex_users_1`, `sqlite_autoindex_users_2`, origin `u`).
  A violation of either raises `sqlite3.IntegrityError`, which
  `POST /users` maps to 409 (`app.py:152-153`).
- **password_hash column confirmed:** name `password_hash`, type `TEXT`,
  `NOT NULL` (`PRAGMA table_info(users)` → `(3, 'password_hash', 'TEXT', 1, None, 0)`).
  No plaintext `password` column exists. A stored value looks like
  `scrypt:32768:8:1$<16-char salt>$<128 hex chars>`.

------------------------------------------------------------------------
## (2) Hashing choice

- **Hash:** `werkzeug.security.generate_password_hash(plain_password)` with
  the default method, which in Werkzeug 3.x is `scrypt` (`n=32768, r=8, p=1`)
  with a random 16-character salt per password (`security_utils.py:3-4`).
  Confirmed by the stored prefix `scrypt:32768:8:1$…`.
- **Verify:** `werkzeug.security.check_password_hash(stored_hash, candidate)`
  (`security_utils.py:6-7`), which re-derives the hash using the method, params
  and salt stored in the string and compares with `hmac.compare_digest`
  (constant-time comparison).
- **Why not encryption:** Encryption is reversible by design, so anyone who
  obtains the key along with the database recovers every user's actual
  password, while the server never needs the plaintext back—only to check that
  a submitted password matches, which a one-way, salted, deliberately slow hash
  does without keeping anything decryptable
  ([OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html):
  passwords should be hashed, not encrypted).

------------------------------------------------------------------------
## (3) Tested failure case

**Request actually sent** (second, identical registration after the first
returned 201):

```
POST /users
Content-Type: application/json

{"username": "test_user", "email": "test@example.com", "password": "secret123"}
```

```
curl -s -X POST http://127.0.0.1:5000/users \
  -H "Content-Type: application/json" \
  -d '{"username": "test_user", "email": "test@example.com", "password": "secret123"}'
```

**Response:** `409` — `{"error": "Username or email already exists"}`

**Why 409 is correct:** The body is well-formed and complete (so not 400) and
registration requires no credentials (so not 401); the request fails only
because it conflicts with the current state of the resource—a user with that
username/email already exists—which is the definition of 409 Conflict in
[RFC 9110 §15.5.10](https://www.rfc-editor.org/rfc/rfc9110#name-409-conflict).
The 409 is driven by the database `UNIQUE` constraint rather than a
check-then-insert, so two concurrent registrations cannot both succeed.

Other status codes observed in the same run:

| Request | Status | Body |
|---|---|---|
| `POST /users` `{"username":"x","email":"x@example.com"}` | 400 | `username, email, and password are required` |
| `POST /login` `{"username":"test_user"}` | 400 | `username and password are required` |
| `POST /login` `{"username":"test_user","password":"wrong"}` | 401 | `Invalid username or password` |
| `POST /login` `{"username":"test_user","password":"secret123"}` | 200 | `{"id": 1, "username": "test_user"}` |

------------------------------------------------------------------------
## (4) Harden next

**Weakness: `POST /login` leaks which usernames exist through response time.**
The 401 message is deliberately generic, but when the username is not found
`app.py:175` short-circuits and skips `verify_password`, so no scrypt work is
done. Measured over 10 requests each with password `wrong`:

| Username | Mean response time |
|---|---|
| `test_user` (exists) | ~102 ms |
| `nobody_here` (does not exist) | ~2 ms |

That ~50× gap lets an attacker enumerate valid usernames despite the identical
error text, which is the precondition for targeted password guessing.

**Fix:** always do exactly one hash verification per login attempt. Precompute a
dummy hash once at startup and verify against it when the user is missing:

```python
# security_utils.py
import secrets
DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32))

# app.py, login()
stored = user["password_hash"] if user else DUMMY_HASH
if not verify_password(stored, password) or not user:
    return jsonify({"error": "Invalid username or password"}), 401
```

Verified on a scratch copy (not committed): with this change the same
measurement gave `test_user` ~111 ms vs `nobody_here` ~124 ms, and correct
credentials still return 200 while unknown users still return 401. Follow up with per-IP/per-username rate limiting on
`/login`, since equal timing slows enumeration but does not stop brute force.

### Also observed (not fixed, for the backlog)

- **`app.run(debug=True)`** (`app.py:183`): an unhandled error returns the
  interactive Werkzeug debugger page with full traceback and source paths.
  Reproduced with `POST /users` and `"password": 123` → 500, because
  `generate_password_hash` calls `.encode()` on an int. Fix: validate that
  `username`, `email`, `password` are strings (400 otherwise) and drive debug
  from an environment variable, off by default.
- **Case-variant duplicates accepted:** after `test_user` / `test@example.com`
  existed, `Test_User` / `TEST@example.com` registered with 201. SQLite `UNIQUE`
  on `TEXT` uses `BINARY` collation (case-sensitive). Fix: normalise email to
  lowercase before insert and declare `username`/`email` `COLLATE NOCASE`.
- **Missing `Content-Type: application/json`** on `/users` or `/login` returns an
  HTML 415 page, not a JSON 400 as the README contract states, because these
  routes call `request.get_json()` without `silent=True` (the recipe routes
  already use `silent=True`).
- **README typo:** the "Bad login (missing password)" example has `- X POST`
  instead of `-X POST`; curl rejects it (`option -: is unknown`, exit 2), so
the example never reaches the server.
