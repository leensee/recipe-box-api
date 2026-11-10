# Recipe Box API

A small, working Flask + SQLite JSON API for keeping recipes, with real user accounts, hashed passwords, and clean status codes on all auth endpoints. In BE104, you extend it with token-based auth, ownership rules, and middleware.

------------------------------------------------------------------------
## Run it

```
pip install -r requirements.txt
python init_db.py
python app.py
```

Requires Python 3.10+.

------------------------------------------------------------------------
## Try it

```
curl http://localhost:5000/recipes
curl http://localhost:5000/recipes/1
curl -X POST http://localhost:5000/recipes \
-H "Content-Type: application/json" \
-d '{"title": "Toast", "ingredients": "bread"}'
curl -X DELETE http://localhost:5000/recipes/1
```
------------------------------------------------------------------------
## Authentication

Register a new user:
```
curl -i -X POST http://localhost:5000/register \
-H "Content-Type: application/json" \
-d '{"username": "test_user", "email": "test@example.com", "password": "secret123"}'
```
Expected: 201 Created with the new user in the response

------------------------------------------------------------------------
Try registering the same user again:
```
curl -i -X POST http://localhost:5000/register \
-H "Content-Type: application/json" \
-d '{"username": "test_user", "email": "test@example.com", "password": "secret123"}'
```
Expected: 409 Conflict and an error about the username or email already existing

------------------------------------------------------------------------
Log in with that user:
```
curl -i -X POST http://localhost:5000/login \
-H "Content-Type: application/json" \
-d '{"username": "test_user", "password": "secret123"}'
```
Expected: 200 OK and basic user info

------------------------------------------------------------------------
Bad login (missing password):
```
curl -i -X POST http://localhost:5000/login \
-H "Content-Type: application/json" \
-d '{"username": "test_user"}'
```
Expected: 400 Bad Request

------------------------------------------------------------------------
Bad login (wrong password):
```
curl -i -X POST http://localhost:5000/login \
-H "Content-Type: application/json" \
-d '{"username": "test_user", "password": "wrong"}'
```
Expected: 401 Unauthorized with a generic "Invalid username or password" message

------------------------------------------------------------------------

## Endpoints

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | / | 200 | |
| GET | /recipes | 200 | 401 invalid token (token optional; adds your private recipes) |
| GET | /recipes/&lt;id&gt; | 200 | 401 · 403 private recipe you don't own · 404 |
| POST | /recipes | 201 | 400 bad body · 401 · 409 duplicate title |
| PATCH | /recipes/&lt;id&gt; | 200 | 400 · 401 · 403 not owner or admin · 404 · 409 |
| DELETE | /recipes/&lt;id&gt; | 204 | 401 · 403 not owner or admin · 404 |
| POST | /register | 201 | 400 bad body · 409 duplicate username/email |
| POST | /login | 200 | 400 missing fields · 401 invalid credentials |

`is_public` controls visibility: anyone can read public recipes, and private
recipes are visible only to their owner (send `Authorization: Bearer <token>`
from `/login`). Creating, editing, and deleting recipes requires a token, and
only the recipe's owner or an admin can edit or delete it.

------------------------------------------------------------------------
