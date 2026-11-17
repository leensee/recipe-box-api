# Recipe Box API

A Flask + SQLite JSON API for storing recipes, with user accounts, token-based authentication, and per-recipe access control.

**Where it started:** an open CRUD skeleton with no notion of users. Anyone could list every recipe (private ones included), edit any recipe, or delete one permanently, all without identifying themselves.

**Where it is now:**

- **Accounts:** registration with scrypt-hashed passwords.
- **Login:** a generic error for every failure, and equalized response times, so neither reveals whether a username exists.
- **Tokens:** a signed JWT issued at login and required on every write.
- **Access control:** owner and admin rules on reading private recipes and on edits and deletes.
- **Input validation:** a JSON 400 for any bad request body, instead of a crash.

## Setup

Requires Python 3.10+.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root with a signing secret. `.env` is git-ignored, so never commit it.

```bash
python -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(32))" > .env
```

The app refuses to start without `JWT_SECRET`. Use at least 32 bytes; the command above generates one.

Then create the database and start the server:

```bash
python init_db.py
python app.py
```

The server runs at `http://localhost:5000`. `init_db.py` seeds three recipes, one of which ("Secret family hot sauce") is private and has no owner. It's safe to run again: it adds any missing columns and indexes to an existing database and only seeds an empty one.

If your `recipes.db` was created before 2026-11-17 and contains usernames or emails that differ only by case (for example `test_user` and `Test_User`), `init_db.py` stops with an `IntegrityError` when it adds the case-insensitive indexes. Rename or remove one account in each duplicate pair, or delete `recipes.db` (which erases all users and recipes) and run `init_db.py` again.

## Authentication

Register, then log in to get a token:

```bash
curl -i -X POST http://localhost:5000/register \
-H "Content-Type: application/json" \
-d '{"username": "test_user", "email": "test@example.com", "password": "secret123"}'

curl -i -X POST http://localhost:5000/login \
-H "Content-Type: application/json" \
-d '{"username": "test_user", "password": "secret123"}'
```

The login response includes a `token`, which is valid for one hour. Send it on protected requests:

```bash
TOKEN=<paste token here>

curl -i -X POST http://localhost:5000/recipes \
-H "Authorization: Bearer $TOKEN" \
-H "Content-Type: application/json" \
-d '{"title": "Toast", "ingredients": "bread", "is_public": false}'
```

Logging out happens on the client: discard the token. The server keeps no sessions.

## Access rules

| Action | Who can do it |
| --- | --- |
| Read a public recipe | Anyone |
| Read a private recipe | Its owner, or an admin |
| List recipes | Anyone sees public recipes; with a token, you also see your own private ones (admins see all) |
| Create a recipe | Any logged-in user (you become its owner) |
| Edit or delete a recipe | Its owner, or an admin |

Usernames and emails are unique regardless of case (`Test_User` and `test_user` count as the same name), and login matches usernames case-insensitively. Case is compared for ASCII letters only.

New accounts have the `user` role. To make an account an admin, update the database directly:

```bash
sqlite3 recipes.db "UPDATE users SET role = 'admin' WHERE username = 'test_user';"
```

The role is read from the token, so log in again afterwards.

## Endpoints

| Method | Path | Auth | Success | Errors |
| --- | --- | --- | --- | --- |
| GET | / | None | 200 | |
| POST | /register | None | 201 | 400 bad body · 409 duplicate username/email |
| POST | /login | None | 200 + token | 400 missing fields · 401 invalid credentials |
| GET | /recipes | Optional | 200 | 401 invalid or expired token |
| GET | /recipes/&lt;id&gt; | Private recipes only | 200 | 401 · 403 not owner or admin · 404 |
| POST | /recipes | Required | 201 | 400 bad body · 401 · 409 duplicate title |
| PATCH | /recipes/&lt;id&gt; | Required | 200 | 400 · 401 · 403 not owner or admin · 404 · 409 |
| DELETE | /recipes/&lt;id&gt; | Required | 204 | 401 · 403 not owner or admin · 404 |

How the error codes are used:

- **401** means the API couldn't establish who you are. A missing or malformed `Authorization` header, an invalid or tampered token, and an expired token each get their own error message (`"Token has expired"` for the last). Every 401 from a token-protected route includes a `WWW-Authenticate: Bearer realm="recipe-box-api"` challenge, adding `error="invalid_token"` when a token was sent but rejected. `/login`'s 401 has no challenge, because it takes credentials in a JSON body and there's no standard scheme for that.
- **403** means you're logged in but not allowed to do that.
- **409** only ever means a real duplicate.

## How it's protected

- **Passwords** are stored as salted scrypt hashes (`security_utils.py`), never as plain text.
- **`@require_auth`** (in `app.py`) guards every write route. It verifies the token's signature and expiry before the route runs, then exposes the caller's identity as `g.current_user_id` and `g.current_user_role`.
- **`can_modify_recipe`** is the single owner-or-admin rule. It decides who can read a private recipe and who can edit or delete any recipe. The owner always comes from the verified token, never from the request.
- **All SQL is parameterized,** so user input is always treated as data, never as part of a query.

The vulnerabilities found and fixed along the way are logged in `SECURITY_NOTES.md`. Test evidence for authentication and authorization is in `SECURITY_AUDIT.md`.

## Known limitations

- **No rate limiting.** `/login` and `/register` are public, and each request runs a deliberately slow scrypt hash, so they're open to brute-force and resource-exhaustion attacks. The fix belongs at an API gateway or proxy.
- **Tokens can't be revoked early.** A token stays valid until it expires, even after the user logs out.
- **No password reset or account recovery.**
- **Development server only.** `python app.py` runs Flask's debug server over plain HTTP. In production, use a proper WSGI server behind HTTPS, so tokens and passwords aren't sent in the clear.
