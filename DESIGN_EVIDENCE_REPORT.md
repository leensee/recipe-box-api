# Design and Evidence Report | recipe-box API

## (1) Users table schema

Confirmed against actual DB (sqlite3 recipes.db ".schema users")

| Field | Type | Constraint(s) | 
|---|---|---|
| id | INTEGER | PRIMARY KEY |
| username | TEXT | NOT NULL, UNIQUE |
| email | TEXT | NOT NULL, UNIQUE |
| password_hash | TEXT | NOT NULL |

Uniqueness constraints enforced:
- One on username that blocks registering a duplicate username.
- One on email that blocks registering a duplicate email.
- The uniqueness comparison for both is case-sensitive because SQLite compares TEXT exactly (byte for byte) by default.
The usernames test_user & Test_User both returned 201 CREATED, as did the emails test@example.com & test@EXAMPLE.com.

password_hash:
- Column is named password_hash 
- Its type & constraints are TEXT NOT NULL
- Every value starts with "scrypt:32768:8:1$" (confirmed by sqlite3 recipes.db "SELECT username, password_hash FROM users;")
- The column name serves as a built-in reminder for other developers (and my future self) to never store raw, unhashed text here. 

## (2) Hashing choice

Method:
- Hash function: generate_password_hash from inside hash_password(plain_password: str)
- Verify function: check_password_hash from inside verify_password(stored_hash: str, candidate: str)
- Both imported from werkzeug.security and contained in the project file security_utils.py
- The method for both is scrypt, the default, as hash_password passes no method arguments, and verify_password calls check_password_hash, which reads the method from the start of the stored string. This is confirmed by every stored value starting with "scrypt:32768:8:1$" as evidenced in field (1).
- When generate_password_hash is called inside hash_password(plain_password: str) during user registration, it returns a formatted string that embeds the algorithm (scrypt), the cost parameters, the unique salt, and the final hash value as shown in the following actual stored password_hash value (abbreviated) & the illustration below it showing what each part of that value actually is:

Stored value (abbreviated): scrypt:32768:8:1$ExyStLEJZ7hYVxGP$16d3030d
What it contains: <algorithm>:<cost parameter n>:<cost parameter r>:<cost parameter p>$<salt>$<hash>

- When check_password_hash is called from inside verify_password(stored_hash: str, candidate: str) during login, Werkzeug automatically parses that information from the stored hash, and uses it to hash the candidate password, comparing the two hashes with hmac.compare_digest (verified in werkzeug/security.py), a constant-time comparison, which means that the time the check takes cannot be used to discern how many characters matched. The candidate password is hashed the same way the stored hash was created and compared, and the stored hash is never reversed or decrypted. 

Why not encryption:
- Storing encrypted passwords is storing the original passwords, just in another form, which the app never needs (it only needs to check for a match), and they usually sit on the same server as the key that can reverse the encryption, so one breach often exposes both the database and key together.

## (3) Tested failure case - Wrong password
- Method: POST
- Path: /login
- Header: "Content-Type: application/json"
- Body: {"username": "demo_user", "password": "wrongaf"}
- Status line: HTTP/1.1 401 UNAUTHORIZED
- Response headers:
  Server: Werkzeug/3.1.9 Python/3.14.6
  Date: Fri, 23 Oct 2026 01:00:21 GMT
  Content-Type: application/json
  Content-Length: 46
  Connection: close
- Response body: {"error": "Invalid username or password"} (whitespace condensed)
- Why it's correct: The JSON body was well-formed and had both required keys, so it was valid (not 400). Login doesn't create or change anything, so a conflict isn't possible here (not 409). The request did not contain valid authentication credentials, which is what 401 is for.  

- Supporting evidence: A login attempt for an account that doesn't exist returns an identical response body and status, as evidenced below:
  - Method: POST
  - Path: /login
  - Header: "Content-Type: application/json"
  - Body: {"username": "not_a_real_username", "password": "alsonotreal"}
  - Status line: HTTP/1.1 401 UNAUTHORIZED
  - Response headers: 
    Server: Werkzeug/3.1.9 Python/3.14.6
    Date: Fri, 23 Oct 2026 01:02:26 GMT
    Content-Type: application/json
    Content-Length: 46
    Connection: close
  - Response body: {"error": "Invalid username or password"} (whitespace condensed)
- Note that Content-Length: 46 matches in both response headers, supporting the identical response bodies in showing that the response content does not reveal which usernames exist and which do not.

- Why it's technically not fully correct: RFC 9110 §15.5.2 (401 Unauthorized)(https://www.rfc-editor.org/rfc/rfc9110#section-15.5.2) states that a server sending a 401 response MUST include a WWW-Authenticate header with at least one challenge (defined in §11.6.1). Neither response has this, and there is no standard scheme for credentials in a JSON body. Adding tokens resolves this for protected routes, which can send WWW-Authenticate: Bearer as defined in RFC 6750 §3 (https://www.rfc-editor.org/rfc/rfc6750#section-3). Because /login will still take a JSON body and still return a 401 without the header, /login itself remains a known gap. 

## (4) Harden next
- Weakness: Username enumeration through response timing on POST /login. Before the fix, a single request was enough to tell whether a username exists. 
- Evidence: Although a real username and an unknown username return identical Content-Length headers, response bodies, and status codes, they do NOT return identical response time, as shown in the table below:

| Username | Mean | Median | Range |
|---|---|---|---|
| demo_user (exists) | 46.98 ms | 46.21 ms | 45.54 to 53.98 ms |
| not_a_real_username (doesn't exist) | 0.81 ms | 0.79 ms | 0.65 to 1.14 ms |

- Data sourced from the following command:
```
for i in {1..10}; do curl -s -o /dev/null -w '%{time_total}\n' -X POST http://localhost:5000/login -H "Content-Type: application/json" -d '{"username": "demo_user", "password": "wrong"}'; done
```
- Second run was same command with "username": "not_a_real_username".

- Cause: original line 175 in app.py
```  
    if not user or not verify_password(user["password_hash"], password):
```
- Reasoning: Python's or stops as soon as the left side is true, so when not user is true, verify_password never runs. Because verify_password is where scrypt runs, and scrypt is purposefully slow, the unknown user path skips the most expensive step completely. The single failure branch designed to prevent malicious callers from guessing valid usernames, as Unit 2 describes it, only protects response content. 
- Fix: Make both paths do one scrypt check using a dummy hash.
  - Edit security_utils.py: add import and one line for DUMMY_HASH
```
# NEW: add secrets to imports
import secrets
```

```
# NEW: add DUMMY_HASH to bottom of file, after def hash_password. Runs once at app startup.
DUMMY_HASH = hash_password(secrets.token_urlsafe(32))
```   

  - Edit app.py: add import and a small change around original line 175
```
# NEW: Add DUMMY_HASH to imports
from security_utils import hash_password, verify_password, DUMMY_HASH 
```    
   
```
    #  NEW: Replace if not user or not verify_password(...) block located inside login(). Place verify_password on its own line so it always runs. 
    if user:
        stored_hash = user["password_hash"]
    else:
        stored_hash = DUMMY_HASH
        
    password_ok = verify_password(stored_hash, password)
        
    if not user or not password_ok:
        return jsonify({"error": "Invalid username or password"}), 401
        
    return jsonify({   
        "id": user["id"],
        "username": user["username"],
    }), 200
```

Verification:
- Login with valid credentials still returns 200
- Both failures still returned 401 in all 20 timed requests.
- Data sourced from the same code as before-fix, with the addition of %{http_code}. Second run used the same unknown username as before-fix.
- The ranges now overlap. (demo_user 45.85 to 63.55 ms, not_a_real_username 45.53 ms to 68.78 ms). Before the fix, they didn't overlap at all, with the slowest unknown user request (1.14 ms) about 40 times faster than the fastest real one (45.54 ms).

|  | demo_user median | not_a_real_username median | Gap |
|---|---|---|---|
| Before the fix | 46.21 ms | 0.79 ms | ~46 ms (about 58 times slower) |
| After the fix | 46.18 ms | 45.94 ms | 0.25 ms (smaller than the variation inside each set; noise) |
 
