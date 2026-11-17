# Security notes

- 2026-10-21: Anonymous GET to `GET /recipes` returns all recipes, including `is_public: false` items (e.g. "Secret family hot sauce"). No auth or identity required.
- 2026-10-21: Anonymous PATCH to `PATCH /recipes/3` succeeds with 200 OK and updates the non-public recipe's `title`. No auth or identity required.
- 2026-10-21: Anonymous DELETE to `DELETE /recipes/3` succeeds with 204 No Content and permanently removes the recipe. No auth or identity required.
- 2026-11-10: Verified fixed: anonymous `PATCH /recipes/3` and `DELETE /recipes/3` now return 401; a valid token for a user who isn't the owner or an admin gets 403.
- 2026-11-10: Fixed: `GET /recipes` now returns only public recipes to anonymous callers, and public recipes plus the caller's own private ones with a valid token. A bad or expired token gets 401. Resolves the 2026-10-21 `GET /recipes` entry.
- 2026-11-17: Fixed: admins can now read any private recipe (`GET /recipes/<id>`) and list every recipe (`GET /recipes`), matching their existing edit/delete access. `get_recipe` now uses the same `can_modify_recipe` owner-or-admin rule as the write routes, so read and write permissions can't drift apart.
- 2026-11-17: Fixed: an expired token now returns 401 `{"error": "Token has expired"}` instead of the generic "Invalid token". The `ExpiredSignatureError` branch had been dropped from `load_authenticated_identity` during the Unit 3 refactor.
- 2026-11-17: Fixed: `init_db.py` now adds the `users.role` column (default `'user'`) to databases created before Unit 3. Previously, `/login` failed with a 500 on those databases.
