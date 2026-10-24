# Security notes

- 2026-10-21: Anonymous GET to `GET /recipes` returns all recipes, including `is_public: false` items (e.g. "Secret family hot sauce"). No auth or identity required.
- 2026-10-21: Anonymous PATCH to `PATCH /recipes/3` succeeds with 200 OK and updates the non-public recipe's `title`. No auth or identity required.
- 2026-10-21: Anonymous DELETE to `DELETE /recipes/3` succeeds with 204 No Content and permanently removes the recipe. No auth or identity required.

