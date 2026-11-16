# Code Review: delivery/faza-1-mvp

Review scope: changes since 0885616 (40 files)

Review request: Changes on branch delivery/faza-1-mvp in 08856168f306f94de5483bfbf8993ce3e36eb671..HEAD, delivered from docs/plans/2026-11-15-faza-1-mvp.md.

## Summary

PatchPoint is a FastAPI + raw `sqlite3` helpdesk MVP with a static HTML/JS client. Linters (ruff, mypy strict), 46 tests (96% coverage), the end-to-end demo and 31 QA scenarios all pass.

The project is a Phase 1 course deliverable: weaknesses W-01…W-18 are required by the plan and registered in `docs/faza-1-dev/rejestr-slabosci.md`. All 18 are present where the register says. Findings tagged `[W-xx · intentional]` are expected and must not be fixed in Phase 1 (choose "Nothing now" / no automatic fixes for them). The findings tagged `[NOT IN REGISTER]` are real issues the register does not list; fix them or add them to the register, because Phase 2 is scored against the register.

| Severity | Count |
|---|---|
| CRITICAL | 2 (both intentional) |
| HIGH | 5 (all intentional) |
| MEDIUM | 10 (9 intentional, 1 not in register) |
| LOW | 14 |

---

## Security findings

### [CRITICAL] SEC-001: [W-15 · intentional] Self-registration can assign the agent role

**ID:** SEC-001
**Location:** `backend/app/schemas.py:17`
**Category:** Security
**OWASP:** A08:2025
**CWE:** CWE-915
**Effort:** trivial

**Problem:**
`UserCreate.role` goes straight into `create_user` (`backend/app/routers/auth.py:28`); `/api/auth/register` needs no login.

**Impact:**
Anyone can register an agent account: read every ticket, change status and assignees.

**Remediation:**

```python
# Before
role=payload.role
# After
role=Role.EMPLOYEE
```

### [CRITICAL] SEC-002: [W-12 · intentional] Default agent account seeded at startup; no password policy; no login throttling

**ID:** SEC-002
**Location:** `backend/app/database.py:14`
**Category:** Security
**OWASP:** A07:2025
**CWE:** CWE-1392
**Effort:** easy

**Problem:**
`DEMO_USERS` (`database.py:13-18`) is seeded by `seed_demo_data` (line 130) because `config.py:14` defaults it on. It creates agents `admin` (password `adm…[REDACTED]`) and `helpdesk`. `password` has no constraints (`schemas.py:14`), and `/login` is not rate limited (also CWE-1393, CWE-521, CWE-307).

**Impact:**
Any fresh instance, including a future container, ships a known agent login. Registration with an empty password returns 201.

**Remediation:**
Default seeding to off, take the bootstrap password from the environment, require a minimum length, rate-limit `/login`.

### [HIGH] SEC-003: [W-14 · intentional] SQL injection in ticket search lets any user take over agent sessions

**ID:** SEC-003
**Location:** `backend/app/routers/tickets.py:86`
**Category:** Security
**OWASP:** A05:2025
**CWE:** CWE-89
**Effort:** easy

**Problem:**
`search` is pasted into `LIKE` twice with an f-string and run without parameters (line 89). The register files this under Information Disclosure; the auditor confirmed (challenger re-verified) a UNION payload returning every session token and password hash, and a stolen agent token then working as a Bearer header.

**Impact:**
Full takeover of agent sessions by any registered user.

**Remediation:**

```python
# Before
f"t.title LIKE '%{search}%' OR t.description LIKE '%{search}%'"
# After
conditions.append("(t.title LIKE ? OR t.description LIKE ?)"); params += [f"%{search}%"] * 2
```

### [HIGH] SEC-004: [W-17 · intentional] Stored XSS through innerHTML

**ID:** SEC-004
**Location:** `frontend/app.js:115`
**Category:** Security
**OWASP:** A05:2025
**CWE:** CWE-79
**Effort:** easy

**Problem:**
API data is written with `innerHTML` in `renderTickets` (110-124), `openTicket` (172-204, e.g. `comment.body` at 178) and the user bar (line 100). The cookie has no `HttpOnly` (W-11).

**Impact:**
A ticket title like `<img src=x onerror=…>` runs in an agent's browser and can read the session cookie.

**Remediation:**

```javascript
// After
td.textContent = ticket.title;
```

### [HIGH] SEC-005: [W-08 · intentional] Predictable session token md5(username:unix_time)

**ID:** SEC-005
**Location:** `backend/app/security.py:17`
**Category:** Security
**OWASP:** A07:2025
**CWE:** CWE-330
**Effort:** trivial

**Problem:**
The token is computable from the username (discoverable via W-05) and the login second; sessions never expire (W-09). Also CWE-340.

**Impact:**
Live agent sessions can be recovered by brute force over a time window.

**Remediation:**

```python
return secrets.token_urlsafe(32)
```

### [HIGH] SEC-006: [W-07 · intentional] Unsalted MD5 password hashing

**ID:** SEC-006
**Location:** `backend/app/security.py:9`
**Category:** Security
**OWASP:** A04:2025
**CWE:** CWE-916
**Effort:** easy

**Problem:**
`hash_password` uses unsalted MD5; `verify_password` (line 13) compares with `==`. Also CWE-328.

**Impact:**
Hashes leaked through W-06 or W-14 crack instantly.

**Remediation:**
Use argon2/bcrypt or `hashlib.scrypt` with a per-user salt and `hmac.compare_digest`.

### [HIGH] SEC-007: [W-16 · intentional] IDOR on ticket details and comments

**ID:** SEC-007
**Location:** `backend/app/routers/tickets.py:94`
**Category:** Security
**OWASP:** A01:2025
**CWE:** CWE-639
**Effort:** easy

**Problem:**
`get_ticket` (94-105) and `add_comment` (159) never check that an employee filed the ticket. Comments are also writable on foreign tickets.

**Impact:**
Any employee can read and comment on every ticket (sequential ids).

**Remediation:**

```python
if user.role == Role.EMPLOYEE and row["reporter_id"] != user.id:
    raise HTTPException(404, "Ticket not found")
```

### [MEDIUM] SEC-008: [W-13 · intentional] CORS reflects any Origin with credentials

**ID:** SEC-008
**Location:** `backend/app/main.py:28`
**Category:** Security
**OWASP:** A02:2025
**CWE:** CWE-942
**Effort:** easy

**Problem:**
`allow_origins=["*"]` with `allow_credentials=True`, all methods and headers (lines 26-32). SameSite=Lax limits cross-site cookie use, but any `http://localhost:<port>` page is same-site.

**Impact:**
A page opened in the same browser can log in and read tokens from responses.

**Remediation:**
Read an explicit origin allow-list from settings; keep credentials only for those origins.

### [MEDIUM] SEC-009: [W-11 · intentional] Session cookie lacks HttpOnly and Secure; token also in JSON and accepted as Bearer

**ID:** SEC-009
**Location:** `backend/app/routers/auth.py:58`
**Category:** Security
**OWASP:** A02:2025
**CWE:** CWE-1004
**Effort:** easy

**Problem:**
`set_cookie` uses defaults; `LoginResponse.token` (line 60) exposes the token and `dependencies.py:34-37` accepts it as Bearer. Also CWE-614.

**Impact:**
XSS (W-17) or a cross-origin reader (W-13) obtains the token.

**Remediation:**

```python
response.set_cookie(SESSION_COOKIE_NAME, token, httponly=True, secure=True, samesite="strict", max_age=3600)
```

### [MEDIUM] SEC-010: [W-09 · intentional] Sessions never expire

**ID:** SEC-010
**Location:** `backend/app/schema.sql:11`
**Category:** Security
**OWASP:** A07:2025
**CWE:** CWE-613
**Effort:** easy

**Problem:**
`sessions` has no expiry column and `get_current_user` (`dependencies.py:32-50`) does not check age.

**Impact:**
A stolen token works forever; W-08 brute force window covers every past login.

**Remediation:**
Add `expires_at` and reject expired sessions in the lookup.

### [MEDIUM] SEC-011: [W-10 · intentional] Logout does not invalidate the server-side session

**ID:** SEC-011
**Location:** `backend/app/routers/auth.py:64`
**Category:** Security
**OWASP:** A07:2025
**CWE:** CWE-613
**Effort:** easy

**Problem:**
`logout` only deletes the cookie, needs no authentication and leaves the `sessions` row.

**Impact:**
After logout the same token as a Bearer header still returns 200 from `/me`.

**Remediation:**

```python
execute(conn, "DELETE FROM sessions WHERE token = ?", (token,))
```

### [MEDIUM] SEC-012: [W-05 · intentional] Account enumeration at login

**ID:** SEC-012
**Location:** `backend/app/routers/auth.py:48`
**Category:** Security
**OWASP:** A07:2025
**CWE:** CWE-204
**Effort:** trivial

**Problem:**
Unknown user gets 404 "does not exist"; wrong password gets 401 "Invalid password" (line 50).

**Impact:**
Valid usernames can be listed, feeding W-08 and brute force.

**Remediation:**
Return the same 401 "Invalid credentials" in both cases.

### [MEDIUM] SEC-013: [W-01 · intentional] Verbose database error handler

**ID:** SEC-013
**Location:** `backend/app/main.py:34`
**Category:** Security
**OWASP:** A10:2025
**CWE:** CWE-209
**Effort:** trivial

**Problem:**
The 500 body carries the SQLite message, full SQL, bound parameters, absolute database path and a traceback (lines 34-46). Also CWE-550.

**Impact:**
Reveals schema and file layout; parameters may contain tokens or hashes; it makes W-14 exploitable.

**Remediation:**

```python
return JSONResponse(status_code=500, content={"detail": "Internal error"})
```

### [MEDIUM] SEC-014: [W-03 · intentional] debug=True hard-coded; /docs, /redoc and /openapi.json public

**ID:** SEC-014
**Location:** `backend/app/main.py:23`
**Category:** Security
**OWASP:** A02:2025
**CWE:** CWE-489
**Effort:** trivial

**Problem:**
Unhandled errors return a traceback page and the schema is public. Also CWE-215.

**Impact:**
Information disclosure without authentication.

**Remediation:**
Take `debug` and docs URLs from settings, off by default.

### [MEDIUM] SEC-015: [W-04 · intentional] /api/health leaks database path and component versions

**ID:** SEC-015
**Location:** `backend/app/routers/health.py:20`
**Category:** Security
**OWASP:** A01:2025
**CWE:** CWE-497
**Effort:** trivial

**Problem:**
Unauthenticated; returns the absolute database path plus SQLite and Python versions.

**Impact:**
Reconnaissance with no authentication.

**Remediation:**

```python
return HealthResponse(status="ok")
```

### [MEDIUM] SEC-016: [W-06 · intentional] password_hash returned by /register, /login and /me

**ID:** SEC-016
**Location:** `backend/app/schemas.py:27`
**Category:** Security
**OWASP:** A01:2025
**CWE:** CWE-200
**Effort:** trivial

**Problem:**
`UserResponse` includes `password_hash`.

**Impact:**
XSS (W-17) reads `/me`; unsalted MD5 (W-07) then yields the plaintext password.

**Remediation:**
Remove the field from the response model.

### [MEDIUM] SEC-017: [NOT IN REGISTER] No request-body limit, no field length limits, no pagination

**ID:** SEC-017
**Location:** `backend/app/schemas.py:77`
**Category:** Security
**OWASP:** A06:2025
**CWE:** CWE-770
**Effort:** easy
**Verified:** challenger confirmed (Starlette 1.10 `max_body_size` defaults to None); cross-verifier merged with the unbounded `GET /api/tickets` performance observation (`tickets.py:74-91`, rendered by `frontend/app.js:110-124`).

**Problem:**
`title`, `description`, comment `body`, `full_name`, `department`, `asset_tag`, `location` have no `max_length` (`schemas.py:15-16,77-82,109`); `list_tickets` returns every row. Reproduced: a ticket with 20 MiB title and 20 MiB description returned 201 and a 41.9 MB list response. `/api/auth/register` reachable without login has the same gap.

**Impact:**
Cheap denial of service and ever-growing agent lists.

**Remediation:**

```python
title: str = Field(min_length=1, max_length=200)
app.add_middleware(RequestBodyLimitMiddleware, max_body_size=64_000)
```

Add `limit`/`offset` (bound parameters) to `list_tickets`; keep the W-14 f-string in Phase 1.

### [LOW] SEC-018: [W-02 · intentional] Duplicate registration returns the raw SQLite constraint message

**ID:** SEC-018
**Location:** `backend/app/routers/auth.py:33`
**Category:** Security
**OWASP:** A10:2025
**CWE:** CWE-209
**Effort:** trivial

**Problem:**
409 detail reads `UNIQUE constraint failed: users.username`.

**Impact:**
Reveals table and column names.

**Remediation:**
Return a fixed message such as `Username unavailable`.

### [LOW] SEC-019: [W-18 · intentional] No security event logging

**ID:** SEC-019
**Location:** `backend/app/routers/auth.py:45`
**Category:** Security
**OWASP:** A09:2025
**CWE:** CWE-778
**Effort:** easy

**Problem:**
`backend/app` makes no logging calls: failed logins, registrations and role assignments are unrecorded.

**Impact:**
Brute force (W-08, W-12) and self-promotion (W-15) leave no trail.

**Remediation:**
Log authentication and role events.

### [LOW] SEC-020: [NOT IN REGISTER] Session tokens stored in plaintext in the database

**ID:** SEC-020
**Location:** `backend/app/schema.sql:12`
**Category:** Security
**OWASP:** A04:2025
**CWE:** CWE-312
**Effort:** easy
**Verified:** challenger downgraded MEDIUM -> LOW: the only way to read `sessions` in scope is W-14, which is already HIGH with the same chain; remains defense in depth.

**Problem:**
`sessions.token` holds the raw bearer value (`auth.py:53-57` inserts it, `dependencies.py:44` looks it up as-is).

**Impact:**
Anyone who can read the table gets working tokens.

**Remediation:**
Store only a SHA-256 of the token and look sessions up by that hash.

### [LOW] SEC-021: [NOT IN REGISTER] No browser security headers (CSP, X-Frame-Options, X-Content-Type-Options)

**ID:** SEC-021
**Location:** `backend/app/main.py:23`
**Category:** Security
**OWASP:** A02:2025
**CWE:** CWE-1021
**Effort:** easy
**Verified:** challenger confirmed LOW; the clickjacking scenario is overstated (cross-site frames do not send the Lax cookie), the CSP gap as defense in depth for W-17 stands.

**Problem:**
Neither the API (`main.py:23-32`) nor the UI (`frontend/index.html:3-9`, `python http.server`) sends these headers.

**Impact:**
No browser-side mitigation for W-17.

**Remediation:**
Add a small ASGI middleware for the API and a CSP meta tag in the UI.

### [LOW] SEC-022: [NOT IN REGISTER] QA start/stop scripts use a predictable shared /tmp directory

**ID:** SEC-022
**Location:** `.av/config.toml:24`
**Category:** Security
**OWASP:** A02:2025
**CWE:** CWE-379
**Effort:** easy

**Problem:**
`d=/tmp/patchpoint-qa`: if the directory exists, `mkdir -p -m 700` leaves its permissions unchanged; database, logs and the pgid file go there and the stop script (44-49) signals the process group named by the pgid file.

**Impact:**
On a shared host another local user can read the QA database/logs or make the stop script signal another process group of the QA user.

**Remediation:**
Use `"${XDG_RUNTIME_DIR:?}/patchpoint-qa"` or `mktemp -d` with an ownership check.

---

## Architecture findings

### [LOW] ARCH-001: Writes spanning several statements are not atomic; a half-finished seed is never repaired

**ID:** ARCH-001
**Location:** `backend/app/database.py:60`
**Category:** Architecture
**Effort:** easy
**Verified:** challenger downgraded MEDIUM -> LOW (no trigger in the shipped setup; reproduction needed an artificial CHECK constraint). Cross-verifier: the transaction scope must wrap commit errors in `DatabaseError`, so W-01 behaviour (`main.py:34-46`) is unchanged.

**Problem:**
`execute()` commits after every statement, so `seed_demo_data` (130-194) runs 8 transactions and `add_comment` (`tickets.py:167-172`) commits the comment and the `updated_at` bump separately. A failed seed leaves a partial dataset that the "users table empty" guard never repairs.

**Impact:**
Duplicate comment on retry; permanently half-seeded database.

**Remediation:**

```python
with conn:
    comment_id = run(conn, "INSERT INTO comments ...", (...))
    run(conn, "UPDATE tickets SET updated_at = ? WHERE id = ?", (now, ticket_id))
```

### [LOW] ARCH-002: Logout leaves the previous user's form state in the page

**ID:** ARCH-002
**Location:** `frontend/app.js:85`
**Category:** Architecture
**Effort:** trivial

**Problem:**
`showAuthView` does not reset `ticketForm`, `filterForm` or `#message`; the next user sees the previous user's draft and filter, and the first list load applies that filter. The logout handler (`app.js:303-310`) also switches views regardless of the `POST /logout` result.

**Impact:**
Data from the previous session visible to the next user in the same browser.

**Remediation:**

```javascript
ticketForm.reset();
filterForm.reset();
showMessage("", false);
```

---

## Maintainability findings

### [LOW] MAINT-001: Demo seed is inline data with inconsistent missing-user handling

**ID:** MAINT-001
**Location:** `backend/app/database.py:86`
**Category:** Maintainability
**Effort:** easy

**Problem:**
`seed_demo_data` is 65 lines; tickets are hand-written calls while users come from `DEMO_USERS`. An unknown reporter raises `ValueError` (line 106) but an unknown assignee silently becomes NULL (100-104); the comment author is looked up a third way (182-184). `insert_demo_ticket` has 10 parameters.

**Impact:**
A typo in seed data creates a silently wrong dataset.

**Remediation:**
Add a `DEMO_TICKETS: Final` table and one `_user_id(conn, username) -> int` helper that raises for reporter and assignee.

### [LOW] MAINT-002: Ticket reload and update field list repeated in the tickets router

**ID:** MAINT-002
**Location:** `backend/app/routers/tickets.py:66`
**Category:** Maintainability
**Effort:** trivial

**Problem:**
The `fetch_one(TICKET_SELECT ...)` -> None check -> `model_validate` sequence appears at 66-70, 96-98 and 151-155 (500 at line 68 but 404 at 153; both uncovered). The updatable fields are listed twice (112 and 135-147).

**Impact:**
Drift between copies; dead branches.

**Remediation:**
Add `_ticket_or_404(conn, ticket_id)` (without ownership checks, so W-16 stays) and drive the update from one column whitelist.

### [LOW] MAINT-003: Redundant `app_settings` alias in `create_app`

**ID:** MAINT-003
**Location:** `backend/app/main.py:15`
**Category:** Maintainability
**Effort:** trivial

**Problem:**
`settings = settings or Settings()` followed by `app_settings = settings` gives one object two names; mypy strict does not need the alias.

**Impact:**
Noise.

**Remediation:**
Delete line 16 and use `settings`.

### [LOW] MAINT-004: Enum values and Polish labels are duplicated between index.html and app.js

**ID:** MAINT-004
**Location:** `frontend/index.html:68`
**Category:** Maintainability
**Effort:** easy

**Problem:**
Category/priority/status options are hard-coded in HTML (68-74, 79-82, 103-107) and again as maps in `app.js:3-26`. Cross-verifier note: build options with DOM nodes (`new Option(...)`) rather than more `innerHTML` strings, so the change does not add W-17 sinks.

**Impact:**
Adding a category requires three edits.

**Remediation:**
Fill the selects once at startup from the label maps.

### [LOW] MAINT-005: Shared test helpers are scattered across test files

**ID:** MAINT-005
**Location:** `backend/tests/test_tickets.py:11`
**Category:** Maintainability
**Effort:** trivial

**Problem:**
`LoginAs`, `UserFactory`, `TicketFactory` are defined only in `test_tickets.py` as implicit aliases; `test_auth.py`/`test_errors.py` repeat raw `Callable[..., ...]`; `seeded_settings` is rebuilt inline at `test_tickets.py:329`; `test_demo_tickets` never asserts its two login responses.

**Impact:**
A failed seeded login would surface as a confusing `TypeError`.

**Remediation:**
Move `type X = ...` aliases and `seeded_settings` into `conftest.py`; assert `status_code == 200` on the logins.

---

## Documentation findings

### [LOW] DOC-001: README repository tree and documentation list omit the QA artifacts added in this scope

**ID:** DOC-001
**Location:** `README.md:42`
**Category:** Documentation
**Drift-class:** decision
**Fix-policy:** needs-decision
**Effort:** easy

**Problem:**
The "Struktura repozytorium" tree (`README.md:19-45`) lists only `faza-1-dev/` and `plans/` under `docs/`, and "Dokumentacja" (98-104) does not link the QA report. Commits `3a61b28` and `4a517ff` added `docs/testing/` and `.av/`.

**Impact:**
The README no longer matches the repository; the QA evidence (31/31 scenarios pass) is not discoverable from it. Adding lines shifts `README.md:NN` citations used in `.av/config.toml` and the QA plan, which must be re-checked in the same change.

**Remediation:**
Add `testing/` (and optionally `.av/`) to the tree, link the QA report under "Dokumentacja", then re-verify the cited line numbers once.

---

## Verification Summary

**Method:** Cross-domain correlation and adversarial review (Cross-Verifier + Challenger)

| Metric | Count |
|---|---|
| Findings verified | 33 |
| False positives removed | 0 |
| Severity adjustments | 2 |
| Cross-analysis findings | 0 |

### Cross-Analysis (Security <-> Quality)
- No composite findings: no single change resolves every basis of a candidate without removing a required W-xx weakness.
- W-16 + ticket-lookup duplication (MAINT-002): the shared helper must not carry an ownership check in Phase 1; Phase 2 then fixes W-16 in one place.
- W-01 + ARCH-001: a transaction helper must wrap commit failures in `DatabaseError` so the W-01 handler behaviour is unchanged.
- W-12 + ARCH-001/MAINT-001: the "users table empty" seed guard means a Phase 2 patch of W-12 does not reach an existing database; patch must rotate/remove the seeded admin or require the README reset.
- W-17 + MAINT-004: do not add more `innerHTML` option strings.
- W-10 + ARCH-002: the UI looks logged out while the server session persists; extend QA scenario FE-03 in Phase 2.
- SEC-022 + DOC-001, and all quality fixes: they move `file:line` citations in `.av/config.toml` and the QA plan; re-check them once after the edits.
- SEC-017 and the unbounded list were one cause reported twice; reported once.
- Coverage gaps (for the register / README, not findings): the register lacks SEC-017, SEC-020, SEC-021, SEC-022; W-14 is filed as Information Disclosure but enables session takeover; W-16 also allows writing comments; README safety advice does not mention W-13 (browse other sites while the API runs).

### Challenged Findings
- SEC-020 (plaintext session tokens) — downgraded MEDIUM -> LOW: reading the table requires W-14, already reported at HIGH with the same chain.
- ARCH-001 (non-atomic writes) — downgraded MEDIUM -> LOW: no trigger in the shipped setup; valid design note ahead of Phase 2.
- SEC-021 — confirmed LOW; clickjacking scenario overstated.
- All 7 other security items and F2-F7, DOC-001 confirmed.

### Rejected by auditors (self-falsification)
- Bandit B608 on `update_ticket` — false positive: fixed SQL fragments, all values bound (`tickets.py:149`).
- CSRF via cross-site form POST — FastAPI requires `Content-Type: application/json`; SameSite=Lax blocks cross-site cookies (challenger verified).
- Cross-user token collision via ':' in usernames — time suffix is 10 digits, no collision.
- TOCTOU on status transition — single worker, no await between check and UPDATE.
- Non-constant-time hash comparison — covered by W-07/W-06.
- SQLite file mode 0644 — home directory is 0700; deployment concern for Phase 3.
- Cleartext HTTP API base URL — local-only by plan; TLS in Phase 3.
- Synchronous sqlite3 in async handlers — mandated by plan.
- Hard-coded passwords in tests/demo script — documented demo accounts.
- 422 errors echo input; committed evidence contains local paths — accepted.
- Quality: blocking I/O in async endpoints, no service/UoW layer, enums imported from schemas, state machine in router, fail-open visibility rule, module-level `app`, `UserResponse` as current-user type, `TicketUpdate` cannot unassign, flat tests layout, `create_user` 6 parameters, `update_ticket` complexity 10, `api()` on non-JSON errors, JSON content type forcing preflight — all required by the plan or not defects.
- Documentation: 8 docs-drift pre-pass hits (cookie attribute names, `localStorage`, `x86_64`, `host:port` strings) are not drift; QA plan "36 new files" miscount; typo "listie" in the register — outside docs/code drift.

### Doctrine-gap candidates
- The weakness register has no completeness check against a scanner baseline.
- No standard for temporary directories in QA start/stop scripts.
- No transaction-boundary convention for raw `sqlite3`.
- No single source of truth for enum values and labels across backend and frontend.
- Line-number citations in config comments and QA plans are never checked automatically.

### Out of scope (scope check)
None.
