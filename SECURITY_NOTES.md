# Security notes

- 2026-10-21: Anonymous GET to `GET /recipes` returns all recipes, including `is_public: false` items (e.g. "Secret family hot sauce"). No auth or identity required.
- 2026-10-21: Anonymous PATCH to `PATCH /recipes/3` succeeds with 200 OK and updates the non-public recipe's `title`. No auth or identity required.
- 2026-10-21: Anonymous DELETE to `DELETE /recipes/3` succeeds with 204 No Content and permanently removes the recipe. No auth or identity required.
- 2026-11-10: Verified fixed: anonymous `PATCH /recipes/3` and `DELETE /recipes/3` now return 401; a valid token for a user who isn't the owner or an admin gets 403.
- 2026-11-10: Fixed: `GET /recipes` now returns only public recipes to anonymous callers, and public recipes plus the caller's own private ones with a valid token. A bad or expired token gets 401. Resolves the 2026-10-21 `GET /recipes` entry.

