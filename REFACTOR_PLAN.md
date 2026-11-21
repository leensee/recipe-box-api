# Refactor plan for recipe API

## Counted facts

- Distinct responsibilities currently in `app.py`: 18

## Acceptance list (public API contract)

1. POST /register with unique username
    - Expect: 201
    - Body: JSON with user_id, username
2. POST /register with duplicate username
    - Expect: 409
    - Body: JSON with error: username already exists
3. POST /login with valid username/password
    - Expect: 200
    - Body: JSON with a JWT token field
4. POST /login with invalid password
    - Expect: 401
    - Body: JSON with error: invalid username or password
5. GET /recipes
    - Expect: 200
    - Body: JSON dict of all public recipes
6. POST /recipes with valid JWT
    - Expect: 201
    - Body: JSON dict containing the newly created recipe
7. POST /recipes with invalid or expired JWT
    - Expect: 401
    - Body: Invalid or expired token
8. POST /recipes with missing JWT
    - Expect: 401
    - Body: JSON with missing token in Authorization header
9. PATCH /recipes/{id} with valid owner token
    - Expect: 200
    - Body: JSON dict containing the updated recipe
10. PATCH /recipes/{id} with valid non-owner token
    - Expect: 403
    - Body: JSON with error: you do not have permission to modify this recipe
11. PATCH /recipes/{id} with valid admin token
    - Expect: 200
    - Body: JSON dict containing the updated recipe
12. DELETE /recipes/{id} with valid owner token
    - Expect: 204
    - Body:
13. DELETE /recipes/{id} with valid non-owner token
    - Expect: 403
    - Body: JSON with error: you do not have permission to delete this recipe
14. DELETE /recipes/{id} with invalid recipe id
    - Expect: 404
    - Body: json with error: recipe with {id} not found

- Total acceptance items: 14

## Target package layout (planned)

recipe_app/
  __init__.py          # later: assemble the app

  auth/
    routes.py          # login, register endpoints
    logic.py           # password hashing, token handling

  recipes/
    routes.py          # recipe CRUD endpoints
    logic.py           # ownership + validation rules

  db/
    connection.py      # get_db, DB setup
    models.py          # later: data structures / queries

  security/
    jwt_utils.py       # JWT encode/decode helpers
    permissions.py     # is_admin, is_owner checks
