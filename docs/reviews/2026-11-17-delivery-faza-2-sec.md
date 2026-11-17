# Code Review: delivery/faza-2-sec

Review scope: changes since 63c3bb5 (53 files)

Review request: Changes on branch delivery/faza-2-sec in 63c3bb50ccd34d7502e368019884c2f3e7c318b8..HEAD, delivered from docs/plans/2026-11-16-faza-2-sec.md. Review only these changes.

## Summary

Phase 2 (SEC) fixes all 18 registered weaknesses and the extra findings of the blind red-team audit: parameterised SQL, ownership checks, Argon2id, hashed random session tokens with expiry, `HttpOnly; Secure; SameSite=Strict` cookies, per-account login lockout, an explicit CORS allow-list, generic error bodies with `error_id`, security headers, request limits, DOM rendering through `textContent` and a CSP in the UI. The delivery checks agree: ruff (with `S`), mypy strict and 122 tests pass at 98% coverage, the PoC script reports 22/22 `[PODATNE]` on the Phase 1 code and 22/22 `[NAPRAWIONE]` on Phase 2, and QA passed 39/39 scenarios.

The review found no CRITICAL or HIGH issue. Twelve issues remain: two MEDIUM security findings (the session cookie is shared by every port on `localhost`; the ticket detail returns an unbounded comment list), three LOW security findings, one LOW performance finding, one LOW maintainability finding and five documentation findings. Most of them are gaps next to the fixed weaknesses, not regressions.

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 5 |
| LOW | 7 |

Scans that ran: ruff (with `S`), mypy strict, `node --check`, semgrep (8 rule sets), bandit, pip-audit, detect-secrets and a regex scan over the 9 commits. Semgrep, bandit and pip-audit report nothing on the changed files.

## Security

### [MEDIUM] SEC-001: Session cookie is sent to every port on localhost

**ID:** SEC-001
**Location:** `backend/app/routers/auth.py:132`
**Category:** Security
**OWASP:** A07:2025
**CWE:** CWE-668
**Effort:** medium

**Problem:**
`set_cookie` (auth.py:132-140) sets the cookie for the host `localhost` only, with no `Domain`. Cookies are not isolated by port (RFC 6265 §8.5). `Secure` does not help, because Chrome and Firefox treat `http://localhost` as a secure context. `SameSite=Strict` still sends the cookie on same-site requests, and a page on another `localhost` port is the same site. `HttpOnly` hides the cookie from JavaScript, not from a server that receives the request. `docs/faza-2-sec/threat-model.md:230` says CORS plus `SameSite=Strict` breaks the CORS-1 attack of actor T3 ("a foreign page on another localhost port") and names only logout as leftover risk. README §9 covers CSRF, not this. Basis: code plus the RFC; not tested in a browser.

**Impact:**
T3 runs a listener on `http://localhost:3000`. A logged-in helpdesk agent opens that page, or any localhost page loads an image from it. The browser sends `Cookie: session=<token>` to port 3000, and the listener replays it against `localhost:8000`. The agent's session is taken for up to 30 minutes idle and 8 hours at most. This bypasses `HttpOnly`, the CORS list and `SameSite`.

**Remediation:**
Add the case to the T3 analysis and to README §9. Locally, serve the UI and API under a dedicated hostname, which is a different site from `localhost`, so services on `localhost:<port>` never get the cookie. For Phase 3: a dedicated HTTPS origin, the `__Host-` prefix, and UI and API on one origin behind a reverse proxy.

```python
# frontend/app.js
const API_BASE_URL = "http://patchpoint.localhost:8000";
# start the API
PATCHPOINT_CORS_ORIGINS='["http://patchpoint.localhost:5500"]' make run   # open the UI at http://patchpoint.localhost:5500
```

---

### [MEDIUM] SEC-002: Ticket detail returns every comment, with no limit or paging

**ID:** SEC-002
**Location:** `backend/app/routers/tickets.py:162`
**Category:** Security
**OWASP:** A06:2025
**CWE:** CWE-770
**Effort:** medium

**Problem:**
`get_ticket` fetches all comments of a ticket with no `LIMIT` (tickets.py:161-164), and nothing caps the number of comments per ticket or per user. Every handler is `async def` on one event loop. SEC-017 of the Phase 1 review covered the body limit, field lengths and paging of the ticket list only, so this is a neighbouring gap, not a fix that was claimed and missed. Measured with `TestClient`: a ticket with 50,050 comments of 2,000 characters returned 200 with 105,344,431 bytes and took 0.52 s, all of it blocking the loop.

**Impact:**
A self-registered employee (T2) posts tens of thousands of comments on one ticket (about 2 minutes per 50,000), then repeatedly requests `GET /api/tickets/{id}`. Each request stalls every other user and builds a response of 100 MB or more. An agent who opens the ticket also freezes the browser. The UI renders every comment in one spread call (`frontend/app.js:245-284`), so comment paging changes the response model and the UI together.

**Remediation:**
Return comments page by page with a server-enforced size limit, either through a separate endpoint with `limit`/`offset` or as the newest N comments plus a total count in the ticket detail. Optionally cap comments per ticket.

```python
@router.get("/{ticket_id}/comments")
async def list_comments(ticket_id: TicketId, user: CurrentUser, conn: DbConnection, request: Request,
                        limit: Annotated[int, Query(ge=1, le=PAGE_SIZE_MAX)] = PAGE_SIZE_DEFAULT,
                        offset: Annotated[int, Query(ge=0, le=MAX_SQLITE_INTEGER)] = 0) -> list[CommentResponse]:
    _visible_ticket(conn, ticket_id, user, request)
    rows = fetch_all(conn, f"{COMMENT_SELECT} WHERE c.ticket_id = ? ORDER BY c.id LIMIT ? OFFSET ?", (ticket_id, limit, offset))
    return [CommentResponse.model_validate(dict(r)) for r in rows]
```

---

### [LOW] SEC-003: client_ip in security events can be forged with X-Forwarded-For

**ID:** SEC-003
**Location:** `backend/app/audit.py:31`
**Category:** Security
**OWASP:** A09:2025
**CWE:** CWE-348
**Effort:** trivial

**Problem:**
`log_security_event` records `request.client.host`. uvicorn 0.54 trusts proxy headers by default and treats `127.0.0.1` and `::1` as trusted proxies. `make run` (`Makefile:13`, the line that causes it) and the QA start-up command in `.av/config.toml` both start uvicorn on `127.0.0.1` without `--no-proxy-headers`. Tested: a login sent with `X-Forwarded-For: 203.0.113.77` was logged with `"client_ip": "203.0.113.77"`.

**Impact:**
An attacker with access to the loopback API can attribute `login_failed` and `access_denied` events to any address, which breaks forensics. A later per-IP alert or block keyed on this field can be dodged or turned against an innocent address. The attacker must already be on loopback, so the loss is small today.

**Remediation:**
Disable proxy headers while there is no proxy. When Phase 3 adds a reverse proxy, set `--forwarded-allow-ips` to the proxy's address only and document it next to the logging section.

```make
run:
	cd $(BACKEND) && uv run uvicorn app.main:app --host $(API_HOST) --port $(API_PORT) --no-proxy-headers
```

---

### [LOW] SEC-004: DEMO_PASSWORD is visible to other local users through the process list

**ID:** SEC-004
**Location:** `scripts/demo.sh:53`
**Category:** Security
**OWASP:** A04:2025
**CWE:** CWE-214
**Effort:** easy

**Problem:**
`demo.sh:53` and `:74` put `DEMO_PASSWORD` on jq's command line (`--arg p`), and `request()` passes the JSON body to curl with `-d "$payload"` (`demo.sh:31`). `/proc/<pid>/cmdline` is readable by every user. Tested: `ps` showed `curl ... -d {"password":"..."} ...` while the request was in flight. The delivery plan prescribed the `jq -n --arg` call, so the plan needs the same correction. The password is that of every seeded account, including the agent `helpdesk`, and in the QA start-up it is `QA_AGENT_PASSWORD`.

**Impact:**
On a shared host another local user reads the agent password during `make demo` and logs in to the loopback API as `helpdesk`.

**Remediation:**
Never put the secret on a command line: pipe it into jq through stdin with a shell builtin, and give the body to curl as `--data-binary @-` from stdin.

```bash
login_payload() { printf '%s' "$DEMO_PASSWORD" | jq -Rsc --arg u "$1" '{username: $u, password: .}'; }
# inside request():
args+=(-H 'Content-Type: application/json' --data-binary @-)
status=$(curl "${args[@]}" "$API_URL$path" <<<"$payload") || status="000"
```

---

### [LOW] SEC-005: Rejected tampering attempts leave no security event

**ID:** SEC-005
**Location:** `backend/app/main.py:80`
**Category:** Security
**OWASP:** A09:2025
**CWE:** CWE-778
**Effort:** easy

**Problem:**
The app registers handlers only for `DatabaseError` and `Exception` (main.py:80-81) and has no `RequestValidationError` handler. The Phase 2 fixes reject `role` on registration (`extra="forbid"`, the former mass-assignment attack), `author_id` or `reporter_id` sent to set fields the client does not own, and out-of-range ids with a 422 and log nothing. The UI never sends these fields, so each such 422 means someone altered the request. Only uvicorn's access line remains, without the field or the user. No test asserts such an event (`test_register_rejects_role_field` checks the 422 and that no user was created).

**Impact:**
Probing and privilege-escalation attempts cannot be seen or attributed in `patchpoint.security`. This is a detection gap, not something an attacker can exploit directly.

**Remediation:**
Add a `RequestValidationError` handler that logs a `validation_failed` warning with the path, the error types and the field locations, never the submitted values, then returns FastAPI's default response. Extend `test_register_rejects_role_field` to assert the event.

```python
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError

async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    log_security_event("validation_failed", request, level=logging.WARNING, path=request.url.path,
                       types=",".join(sorted({e["type"] for e in errors})),
                       fields=",".join(".".join(map(str, e["loc"])) for e in errors)[:200])
    return await request_validation_exception_handler(request, exc)

app.add_exception_handler(RequestValidationError, validation_error_handler)
```

---

## Performance

### [LOW] PERF-001: Registration hashes passwords with Argon2 on the event loop

**ID:** PERF-001
**Location:** `backend/app/routers/auth.py:45-55`
**Category:** Performance
**Effort:** easy

**Problem:**
`register` is an `async def` endpoint that calls `hash_password` synchronously through `create_user` (`backend/app/database.py:184`). Argon2id with t=3, m=64 MiB, p=4 takes about 36 ms per hash, and it runs on the event-loop thread. Probes: `/api/health` took 11.5 ms idle and 723.2 ms during 20 concurrent registrations; the same effect shows for logins (13.7 ms to 761.5 ms). Argon2 releases the GIL (8 hashes: 301 ms sequential, 208 ms in 8 threads). The login handler's cause is already a recorded residual risk in `docs/faza-2-sec/README.md:191`, which names only login. Because login with changing usernames already triggers unlimited Argon2 work (`simulate_password_check`), registration adds no new attack capability, which is why this is LOW.

**Impact:**
Anonymous clients can make the single uvicorn worker unresponsive. The risk is accepted for login in the report but not named for registration.

**Remediation:**
Keep the endpoints `async def` and move only the Argon2 calls into `run_in_threadpool`, in `register` and `login` together. Keep the lockout exact: once an `await` sits between `is_login_blocked` and `record_login_failure`, concurrent guesses can all pass the check, so record the attempt before verifying and clear it on success. Then update `docs/faza-2-sec/README.md:191`.

```python
from fastapi.concurrency import run_in_threadpool

async def register(payload: UserCreate, request: Request, conn: DbConnection) -> UserResponse:
    password_hash = await run_in_threadpool(hash_password, payload.password)
    ...
```

---

## Maintainability

### [LOW] MAINT-001: Security-event log helper is copied into three test modules

**ID:** MAINT-001
**Location:** `backend/tests/test_auth.py:37-42`
**Category:** Maintainability
**Effort:** trivial

**Problem:**
An identical `security_events(caplog)` helper is defined in `test_auth.py:37-42` and `test_ticket_security.py:13-18`, and written inline in `test_sessions.py:143-147`. `test_errors.py:40` and `:78` repeat the same filter for `patchpoint.errors`. `count_users` is defined twice with different signatures (`test_auth.py:29` takes `(settings, username)`, `test_database.py:24` takes `(database_path)`). `tests/support.py` exists to hold shared test helpers (MAINT-005 of the Phase 1 review, which covered type aliases and `seeded_settings`; this is new duplication, not a regression of that fix).

**Impact:**
If the log format changes, five places must be edited, and two helpers with one name and different signatures are easy to misuse. Adding a `validation_failed` event (SEC-005) would add a sixth copy.

**Remediation:**
Add one helper to `tests/support.py` and import it everywhere.

```python
def log_events(caplog: pytest.LogCaptureFixture, logger: str = "patchpoint.security") -> list[dict[str, Any]]:
    return [json.loads(r.getMessage()) for r in caplog.records if r.name == logger]
```

---

## Documentation

### [MEDIUM] DOC-001: The Phase 2 report says security headers are on all responses, but two kinds of response skip them

**ID:** DOC-001
**Location:** `docs/faza-2-sec/README.md:118`
**Category:** Documentation
**Drift-class:** decision
**Fix-policy:** needs-decision
**Effort:** easy

**Problem:**
The report says `SecurityHeadersMiddleware` adds the common headers to every response ("do wszystkich odpowiedzi") and the API-only headers to every `/api/` response. Two kinds of response are produced outside that middleware (related change: `backend/app/main.py:69-81`):
1. CORS preflights: `CORSMiddleware` is added last and so is outermost; it answers preflights without calling the inner app (`starlette/middleware/cors.py:86-89`).
2. 500s for unhandled exceptions: the `Exception` handler goes to `ServerErrorMiddleware`, which sits outside all user middleware (`fastapi/applications.py:1039-1050`).

No test checks headers on either path (`test_platform.py:32-43` covers `/api/health` and `/docs`). Both responses have fixed bodies without attacker-controlled content, so this is an overclaim without an exploitable effect, rated MEDIUM after verification.

**Impact:**
This is the "Sec" section of the DevSecOps report. Readers will assume `nosniff`, frame denial, CSP and `no-store` cover every API response.

**Remediation:**
Choose one. Fix the code: register `SecurityHeadersMiddleware` after `CORSMiddleware` so it becomes outermost, set the headers on the response built by `internal_error_handler`, and add tests for a preflight and for `/api/test-failure`. Or narrow the text, for example "…do odpowiedzi aplikacji; odpowiedzi preflight CORS i 500 dla nieobsłużonych wyjątków (ServerErrorMiddleware) ich nie mają".

---

### [MEDIUM] DOC-002: The README says the API accepts requests only from listed origins, but CORS does not filter requests

**ID:** DOC-002
**Location:** `README.md:17`
**Category:** Documentation
**Drift-class:** decision
**Fix-policy:** needs-decision
**Effort:** trivial

**Problem:**
`README.md:17` says "API przyjmuje żądania tylko z originów z listy `PATCHPOINT_CORS_ORIGINS`". CORS only decides which origins a browser lets read responses and when a preflight is required. The API still processes simple requests from any origin: `backend/tests/test_cors.py:47-51` asserts HTTP 200 for a `GET /api/health` from a foreign origin, and the report lists same-site `POST /api/auth/logout` as a residual risk (`docs/faza-2-sec/README.md:89`, `:190`). Related change: `backend/app/main.py:71-78`, `backend/app/config.py:18`.

**Impact:**
The README summary presents CORS as access control, which is the misconception the CORS-1 attack vector relies on. It also contradicts the residual-risk list. Together with SEC-001, the sentence overstates what the allow-list protects.

**Remediation:**
Reword: "Przeglądarka udostępnia odpowiedzi API (z poświadczeniami) tylko originom z listy `PATCHPOINT_CORS_ORIGINS`; API nie odrzuca żądań po originie (patrz ryzyka rezydualne w raporcie z Fazy 2)." Mention the cookie scope when SEC-001 is resolved.

---

### [MEDIUM] DOC-003: The README still sends readers to the Phase 1 report for the API description

**ID:** DOC-003
**Location:** `README.md:17`
**Category:** Documentation
**Drift-class:** decision
**Fix-policy:** needs-decision
**Effort:** trivial

**Problem:**
The diff edited this sentence but kept "Szczegóły, diagramy i opis API znajdują się w raporcie z Fazy 1". That report describes the `ab08633` contract, which Phase 2 changed: the health endpoint returns versions and the database path (`docs/faza-1-dev/README.md:169`), login returns `token` and can answer 404 (`:171`), logout only clears the cookie (`:172`), Bearer authentication is accepted (`:203`), Swagger is at `/docs` (`:52`, `:165`) and demo data is seeded by default (`:131`). The current contract is described only in `docs/faza-2-sec/README.md` §7 and `docs/faza-2-sec/dowody/openapi.json`. Related change: `backend/app/routers/auth.py:83-143`, `backend/app/routers/health.py:10-14`, `backend/app/config.py:15,17`.

**Impact:**
A reader who follows the README's pointer gets a contract that has been superseded, including three security-relevant behaviours that Phase 2 reversed.

**Remediation:**
Point the API description at the Phase 2 report §7 and `docs/faza-2-sec/dowody/openapi.json`, and label the Phase 1 report as a description of the `ab08633` state. The Phase 1 report is a frozen snapshot, so fix the pointer, not the snapshot.

---

### [LOW] DOC-004: The event table implies internal_error contains client_ip, but it does not

**ID:** DOC-004
**Location:** `docs/faza-2-sec/README.md:125`
**Category:** Documentation
**Drift-class:** decision
**Fix-policy:** needs-decision
**Effort:** trivial

**Problem:**
The table header reads "Pola (poza `client_ip`)", which suggests that every row also carries `client_ip`. Line 123 limits "all contain `client_ip`" to the `patchpoint.security` events, and row `:137` labels `internal_error` as logger `patchpoint.errors`, so only the column header is ambiguous. `internal_error` is written by `backend/app/main.py:20-33` through its own `json.dumps` and has no `client_ip`; only `log_security_event` adds it (`backend/app/audit.py:31-32`). Related to SEC-003: the value of `client_ip` is the TCP peer unless proxy headers are disabled.

**Impact:**
Anyone building a log parser or an alert from this table will expect `client_ip` on `internal_error` records.

**Remediation:**
Add "(bez `client_ip`)" to the `internal_error` row, or move that row out of the table. State where `client_ip` comes from once SEC-003 is fixed.

---

### [LOW] DOC-005: `make security-check` is documented as 22 checks, but by default 2 are skipped

**ID:** DOC-005
**Location:** `README.md:140`
**Category:** Documentation
**Drift-class:** decision
**Fix-policy:** needs-decision
**Effort:** easy

**Problem:**
`README.md:140`, `:49` and `:87` describe `make security-check` as running 22 security regression checks with `[PODATNE]`/`[NAPRAWIONE]` results. The Makefile passes neither `DB_PATH` nor `API_LOG` (`Makefile:33-34`), so W-18 and SEC-020 are reported as `POMINIĘTE` and W-07 falls back to an API-only check (`scripts/security_check.sh:229-230`, `:442-451`). A default run ends with `naprawione=20, pominięte=2`. The README never mentions `DB_PATH`, `API_LOG` or `[POMINIĘTE]`. The QA plan says the same at `docs/testing/plans/2026-11-17-patchpoint-phase-2-security-test-plan.md:798` ("22 `[NAPRAWIONE]`"). "22 sprawdzenia" is literally true (22 run, 2 skipped), so LOW.

**Impact:**
Users cannot reproduce the documented 22/22 result with the documented command, and the only end-to-end check of security logging (W-18) is skipped by default.

**Remediation:**
Document `DB_PATH` and `API_LOG` (for example `DB_PATH=backend/data/patchpoint.db API_LOG=<log> make security-check`), add `[POMINIĘTE]` to the tree comment and correct the QA plan line, or pass both variables through the Makefile target.

---

## Verification Summary

**Method:** Cross-domain correlation and adversarial review (Cross-Verifier + Challenger)

| Metric | Count |
|---|---|
| Findings verified | 12 |
| False positives removed | 1 |
| Severity adjustments | 3 |
| Cross-analysis findings | 0 |

### Cross-Analysis (Security <-> Quality)

- Comments without paging (SEC-002) and Argon2 on the event loop (PERF-001): two separate ways to stall the single event loop, and registration creates the T2 account the comment attack needs. Fixing only one leaves the other path open. Two changes, so not a composite.
- Forged `client_ip` (SEC-003) and Argon2 on the event loop (PERF-001): a registration flood leaves only `user_registered` events, and their `client_ip` can be chosen through `X-Forwarded-For`. Fix `Makefile:13` before adding any per-IP throttle on `/register`.
- Missing tampering event (SEC-005) and duplicated test helper (MAINT-001): no test could show the missing event; add the shared helper first, then the handler and its test.
- Cookie scope (SEC-001) and the CORS wording in the README (DOC-002): the README presents the CORS list as access control while a listener on another `localhost` port receives the cookie itself. The Cross-Verifier proposes raising DOC-002 to HIGH; the Challenger's severity (MEDIUM) is kept here.
- Forged `client_ip` (SEC-003) and the event table (DOC-004): an alert keyed on `client_ip` would see nothing for `internal_error` and could be spoofed for the other events. Fix `Makefile:13` first.
- Missing tampering event (SEC-005) and the headers claim (DOC-001): both come from the middleware and handler wiring in `main.py:69-81`, which §6 of the report describes as complete. One pass over that wiring fixes both.
- `security-check` skips W-18 by default (DOC-005) and W-18 only greps for `login_failed`, so it cannot catch a forged `client_ip` (SEC-003) or a missing tampering event (SEC-005).
- Event format (MAINT-001, DOC-004): no single place defines it, not the code, the tests or the docs.

Coverage gaps noted by the Cross-Verifier, not reported as findings: the shell scripts got no shellcheck run (shellcheck is not installed); `frontend/app.js:245-284` renders every comment in one spread call (relevant to SEC-002); other `async` handlers with synchronous SQLite (for example the `LIKE` search) were not measured as data grows.

### Challenged Findings

- CQ-01 (Argon2 on the event loop in registration): downgraded MEDIUM to LOW (now PERF-001). The claimed difference between registration and login does not hold: login with changing usernames already triggers unlimited Argon2 work, and the risk class is already accepted in `docs/faza-2-sec/README.md:191`. Only the documentation gap remains.
- DOC-001 (headers on all responses): downgraded HIGH to MEDIUM. The facts hold, but the responses that miss the headers have fixed bodies without attacker-controlled content.
- DOC-004 (event table): downgraded MEDIUM to LOW. Line 123 already limits the `client_ip` claim to `patchpoint.security`; only the column header is ambiguous.
- DOC-005 of the documentation auditor (the "Próba 2" heading names `audyt-red-team.md`): removed as a false positive. The delivery plan requires the prompts section to be quoted word for word, and the artifact's wording names the planning session's own file. The intro of `audyt-red-team.md` links the correct result file. (The remaining documentation issues were renumbered; the auditor's DOC-006 is DOC-005 here.)
- CQ-02: confirmed, but "undoes MAINT-005" overstated: MAINT-005 covered type aliases and `seeded_settings`, both still shared.
- SEC-002: confirmed; the claim that the report marks SEC-017 as falsely fixed was corrected (SEC-017 never covered comments).

### Rejected by auditors (self-falsification)

- Argon2 verification blocks the event loop in login — documented in `docs/faza-2-sec/README.md:191`.
- Per-account lockout enables lockout of someone else's account — documented and deferred to the network edge.
- Registration's 409 reveals which usernames exist — accepted risk, documented.
- A same-site page can log the user out with a simple POST — documented in `threat-model.md:231` and README.
- CSRF through `text/plain` or no Content-Type — disproved: FastAPI enforces `strict_content_type`.
- UI can be framed (no `frame-ancestors`) — deferred to the static server in Phase 3.
- 500s from unhandled `Exception` lack the security headers — LOW, fixed body (covered by DOC-001 on the documentation side).
- Forged log lines through the username field — disproved: `json.dumps` escapes control characters.
- 422 responses echo the submitted password — returned only to the sender under `Cache-Control: no-store`, never logged.
- Race between the lockout check and recording a failure — no `await` between them on a single worker.
- `security_check.sh` puts throwaway PoC passwords and tokens on curl's command line — negligible; the real demo password is SEC-004.
- detect-secrets: 12 false positives (file references, test fixtures, deliberately wrong passwords, a SHA-256 in the loop-state file).
- `cors_origins` accepts `"null"` or origins without a scheme — requires operator misconfiguration.
- Quality: `database.py` mixes seed data; `sessions.py` combines lifecycle and throttling; a write on every authenticated request; dummy hash at import; `app.database` depends on `Request` through `app.audit`; mutable list default; repeated user column lists; duplicated 401 branches; long functions; PLR0913 on `list_tickets`; unparametrised expiry tests; `reason: str`; frontend GET `Content-Type` — all dictated by the plan, pre-existing or below the thresholds.
- Documentation: 72 LINEREF hits in the verbatim audit output (pinned to `ab08633`); NAME_MISSING false positives (`PATCHPOINT_*`, `app_settings`, `insertAdjacentHTML`, `BaseException`, `x86_64`, the Starlette library path); Phase 1 report outdated (frozen snapshot); seed password policy attributed to `config.py`; the ~44 ms figure is a runtime measurement.

### Doctrine-gap candidates

- No rule for passing secrets to child processes (SEC-004).
- No rule that every collection in a response is bounded (SEC-002).
- The security event list has no "tampered request" category (SEC-005).
- No rule that blocking or CPU-bound work in async endpoints goes through `run_in_threadpool` (PERF-001).
- Documents pinned to a commit have no marker, so the drift pre-pass produced 76 false positives.
- Security-property claims in the report have no rule that a regression test backs them (DOC-001, DOC-002).

### Out of scope (scope check)

None.
