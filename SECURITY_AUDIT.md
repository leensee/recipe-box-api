# Security Audit – Recipe API
  
## 1. Safe Password Storage
- **Database:** SQLite  
- **Password field:** scrypt hash string (not readable, long random-looking value)  
- **Conclusion:** Passwords are stored as hashes, not plaintext.
  
## 2. Authentication (Identity) Checks
**Endpoint tested:** POST /recipes  

- No token:
  - Request: POST /recipes (no Authorization header)
  - Result: 401 UNAUTHORIZED — {"error": "Missing or invalid Authorization header"}
- Bad token:
  - Request: POST /recipes with `Authorization: Bearer this.is.a.bad.token`
  - Result: 401 UNAUTHORIZED — {"error": "Invalid token"}
- Valid user token:
  - Request: POST /recipes with valid Bearer token
  - Result: 201 CREATED — recipe JSON returned  

**Conclusion:** Endpoint correctly requires a valid JWT and returns 401 for missing/invalid identity.

## 3. Authorization (Access Control) Checks
**Endpoints tested:** DELETE /recipes/5 and DELETE /recipes/3
  
- No token:
  - Request: DELETE /recipes/5 (no Authorization header)
  - Result: 401 UNAUTHORIZED — {"error": "Missing or invalid Authorization header"}
- Bad token:
  - Request: DELETE /recipes/5 with `Authorization: Bearer this.is.a.bad.token`
  - Result: 401 UNAUTHORIZED — {"error": "Invalid token"}
- Owner token:
  - Request: DELETE /recipes/5 with valid owner Bearer token
  - Result: 204 NO CONTENT
- Other user token:
  - Request: DELETE /recipes/3 with non-owner valid Bearer token
  - Result: 403 FORBIDDEN — {"error": "You do not have permission to delete this recipe"}
- Admin token:
  - Request: DELETE /recipes/3 with valid admin Bearer token
  - Result: 204 NO CONTENT
  
**Conclusion:** Only the owner or admin can delete; 401 vs 403 are used correctly.

## 4. Centralized Protections
- **Decorator/middleware:** `@require_auth` → `load_authenticated_identity`  
- **Protected routes using it:** POST /recipes, PATCH /recipes/<id>, DELETE /recipes/<id>  
- **Conclusion:** Auth checks are centralized; no ad-hoc per-route token parsing.
