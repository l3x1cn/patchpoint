# Test Plan: PatchPoint Phase 2 (SEC) — hardened API, sessions and static client

## Source
- Type: last 7 commits
- Base: main
- Range: `HEAD~7...HEAD` (`63c3bb5`..`303c431`)
- Date: 2026-11-17
- Branch: delivery/faza-2-sec
- Head: 303c431f80a0ee6b33e93d74d428111dd5092562

## Changes Summary

The last seven commits on `delivery/faza-2-sec` deliver Phase 2 (SEC) of PatchPoint: an AI red-team audit and threat model of the Phase 1 code, fixes for the registered weaknesses W-01…W-18 and the review items SEC-017, SEC-020, SEC-021 and RT-13 in the API and the static client, a PoC regression script and the phase documentation. Every commit carries `Delivery-Plan: docs/plans/2026-11-16-faza-2-sec.md`; that path passed validation (repository-relative, no `..` segment, no symlinked component, a regular file inside the repository), and its Context, Task 1–7 blocks and Verification section are this plan's specification. No trailer was rejected.

| Commit | Delivery-Task-Title | Delivery plan task |
|---|---|---|
| `463f712` | Audyt Red Team i threat model na kodzie Fazy 1 | Task 1 |
| `6f742bc` | Backend — bezpieczna konfiguracja, obsługa błędów, nagłówki i limity | Task 2 |
| `b295c85` | Backend — hasła, sesje, logowanie i dane demo | Task 3 |
| `dfc2547` | Backend — zgłoszenia: SQL injection, IDOR, limity, paginacja i audyt zmian | Task 4 |
| `c092230` | Frontend — bezpieczne renderowanie, CSP, paginacja i obsługa sesji | Task 5 |
| `4bfaeb1` | Skrypty — PoC bezpieczeństwa, demo i konfiguracja QA | Task 6 |
| `303c431` | Dokumentacja Fazy 2 — raport Sekcji Sec, dziennik promptów i dowody | Task 7 |

Changed files by class:
- BE — the FastAPI app on the `backend` target: `backend/app/main.py` (docs off by default, body limit, security headers, CORS allow-list, one generic 500 handler), `middleware.py` (new security-header middleware), `audit.py` (new JSON security log), `config.py` (new settings), `security.py` (Argon2id, random session tokens and their SHA-256, password policy), `sessions.py` (new: sessions with idle and absolute expiry, login-failure counter), `schema.sql` (hashed `sessions`, `login_failures`, `user_version = 2`), `database.py` (transactions, schema-version check, opt-in demo seed), `dependencies.py` (cookie-only authentication), `schemas.py` (`extra="forbid"`, length limits, no `password_hash`) and the routers `auth.py`, `health.py`, `tickets.py`.
- FE — the static client on the `ui` target: `frontend/app.js` (DOM built only with `textContent`/`append`/`new Option`, pagination, 401 handling, readable errors, view reset), `frontend/index.html` (CSP and referrer meta tags, empty selects, field limits, pagination controls), `frontend/styles.css` (pagination, disabled buttons).
- neither — `.av/config.toml`, `.gitignore`, `Makefile`, `README.md`, `backend/pyproject.toml` and `backend/uv.lock` (the `argon2-cffi` dependency, whose effect BE-10 checks, and Ruff `S` rules), `backend/tests/**` (pytest suite), `docs/faza-2-sec/**` (audit, threat model, report, evidence), `scripts/demo.sh` and `scripts/security_check.sh` (repository tooling whose API probes the BE scenarios mirror). No DESKTOP code changed.

Intended contract (delivery plan Tasks 2–5 and Verification, docs/plans/2026-11-16-faza-2-sec.md:297-771 and :1202-1246):
- Platform: `GET /api/health` → `200` `{"status": "ok"}` and nothing else. `/docs`, `/redoc` and `/openapi.json` → `404` unless `PATCHPOINT_DOCS_ENABLED`. Every response that passes through `SecurityHeadersMiddleware` — routed, `404` and `413` responses alike — carries `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and `Referrer-Policy: no-referrer`, and on `/api/` paths also `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` and `Cache-Control: no-store`; CORS preflight answers, which `CORSMiddleware` sends without calling the inner app (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:86-89), and the `500` that `ServerErrorMiddleware` sends, outside the user middleware, for an exception without its own handler (backend/.venv/lib/python3.14/site-packages/fastapi/applications.py:1039-1050) carry none of them. Request bodies above 65,536 bytes → `413`, still with CORS headers. CORS admits only `http://localhost:5500`, with credentials, methods GET/POST/PATCH and the `Content-Type` header; a foreign-origin preflight → `400`. Database and unhandled errors → `500` `{"detail": "Internal server error", "error_id": <32 hex>}`, details only in the `patchpoint.errors` log.
- Accounts and sessions: sign-up → `201` employee; unknown fields such as `role` → `422`; passwords of 15–128 characters that do not contain the username; usernames `[A-Za-z0-9._@+-]{3,50}`; a taken username → `409` `Username is already taken`; Argon2id hashes. Login → `200` `{"user": …}` plus the `session` cookie (`HttpOnly; Secure; SameSite=Strict; Max-Age=28800; Path=/`), its token from `secrets.token_urlsafe(32)` stored as SHA-256; unknown username and wrong password → the identical `401` `Invalid username or password`; five failures in 15 minutes per username → `429` `Too many failed login attempts. Try again later.` with `Retry-After: 900`; a success clears the count. Authentication by cookie only (no Bearer); sessions end after 30 idle minutes or 8 hours. Logout deletes the server session and the cookie and always answers `200`. No response contains `password_hash`. Demo accounts exist only on request, with `PATCHPOINT_DEMO_PASSWORD` and without `admin`.
- Tickets: one static parameterised list query; `search` matched literally (`LIKE … ESCAPE '\'`, at most 100 characters); `limit` 1–100 (default 50); `offset` 0…2⁶³−1; newest first. A single ownership check answers `404` `Ticket not found` for foreign and missing tickets alike. Ids outside 1…2⁶³−1 → `422`. Title ≤ 200, description ≤ 5000, asset tag ≤ 50, location ≤ 100, comment ≤ 2000 characters; unknown fields → `422`. The agent-only PATCH writes one static `COALESCE` update.
- Client: API data reaches the DOM only as text; CSP and `no-referrer` meta tags; select lists filled from the label maps; HTML length limits matching the API; pages of 50 rows with "Poprzednia"/"Następna"; a 401 during work returns to the sign-in view with `Sesja wygasła lub została zakończona — zaloguj się ponownie.`; logout resets forms and messages; error text is the string `detail` or the joined `msg` values.

Coverage of the Phase 1 findings: W-01 BE-20 · W-02 BE-10 · W-03 BE-02 · W-04 BE-01 · W-05 BE-13, BE-14, BE-17 · W-06 BE-10, BE-12 · W-07 BE-10 · W-08 BE-12 · W-09 BE-12 · W-10 BE-19, FE-02 · W-11 BE-12, FE-02 · W-12 BE-10, BE-14–BE-18, FE-09 · W-13 BE-03–BE-08 · W-14 BE-20 · W-15 BE-11 · W-16 BE-23, BE-26 · W-17 FE-04, FE-08 · SEC-017 BE-09, BE-21, BE-28, FE-10 · SEC-020 BE-12 · SEC-021 BE-01, FE-08 · RT-13 BE-29. W-18 (security log) is out of harness scope.

BE State Checks read the SQLite database under the store name `patchpoint`: the file `PATCHPOINT_DATABASE_PATH` points to (backend/app/config.py:14), which the QA bring-up creates at `.av/run/patchpoint.db` (.av/config.toml:33-34). The config defines no `[env.stores]` yet, so `plan check` reports `missing.stores: patchpoint`. The checks cover behaviour no HTTP response reveals: Argon2id hashes, hashed session tokens and their 8-hour lifetime, login-failure counts, deleted sessions and the schema version.

## Blockers / Findings

None found.

`backend/app/` and `frontend/` contain no debug artefacts, `TODO`/`FIXME`/`HACK`/`DEBUG` markers, short-circuits or disabled authentication or ownership guards, and each endpoint returns the statuses and messages that delivery-plan Tasks 2–5 specify.

## Users
- owner: registered — plain employee (sign-up always yields `employee`) who files and follows tickets; username `qa+$QA_TAG-owner@test.local`, full name `QA Owner $QA_TAG`, department `QA`
- other: registered — second employee whose ticket owner must not reach (BE); username `qa+$QA_TAG-other@test.local`, full name `QA Other $QA_TAG`, department `QA`
- locked: registered — employee driven into the login lockout and used for nothing else (BE-15, BE-16, FE-09); username `qa+$QA_TAG-locked@test.local`, full name `QA Locked $QA_TAG`, department `QA`
- retry: registered — employee showing that a successful login resets the failure count (BE-18); username `qa+$QA_TAG-retry@test.local`, full name `QA Retry $QA_TAG`, department `QA`
- leaver: registered — employee whose sessions are ended by logout (BE-19); username `qa+$QA_TAG-leaver@test.local`, full name `QA Leaver $QA_TAG`, department `QA`
- xss: registered — employee whose full name and ticket fields carry HTML and script payloads (FE-04); username `qa+$QA_TAG-xss@test.local`
- pager: registered — employee who files 51 tickets so that the list has a second page, and nothing else (FE-10); username `qa+$QA_TAG-pager@test.local`, full name `QA Pager $QA_TAG`, department `QA`
- agent: existing — Helpdesk agent (role `agent`, `qa.users.agent`), the seeded demo agent: only agents list every ticket and may change one, and sign-up cannot create one (backend/app/routers/auth.py:54). PatchPoint logs in by username, so `$QA_AGENT_EMAIL` holds it; qa-redact masks that value in BE output, so no scenario asserts the agent's username.

Anonymous requests send no credential: BE-01–BE-09, the no-cookie edge cases and FE-08. The usernames `qa+$QA_TAG-nobody@test.local`, `qa+$QA_TAG-ghost@test.local`, `qa+$QA_TAG-free@test.local` and `qa+$QA_TAG-escalate@test.local` are never registered.

## Detected Tools
- Playwright MCP: available (OMP built-in browser)
- HTTP client: curl (httpie unavailable); jq and perl JSON::PP available
- Store clients: sqlite3 and psql available; mysql and redis-cli unavailable. State Checks use the SQLite store `patchpoint`, which the config does not define yet.
- Desktop drivers: none

## FE Test Scenarios

Every FE scenario runs in the browser on the `ui` target, whose page calls the API at `http://localhost:8000` (frontend/app.js:1). Ticket titles carry `$QA_TAG`, so list assertions are unaffected by other data.

### State combinations — client response handling (FE-01, FE-02, FE-03, FE-05, FE-06, FE-09)

`api()` (frontend/app.js:82-113) branches on three inputs: whether the response is ok, whether its status is 401, and whether a user is signed in (`currentUser`).

| # | `response.ok` | Status 401 | `currentUser` set | Classification | Client behaviour | Scenario |
|---|---|---|---|---|---|---|
| 1 | yes | no | yes | real | returns the body; the view updates | FE-05 |
| 2 | yes | no | no | real | returns the body (sign-in, sign-up) | FE-02 |
| 3 | yes | yes | yes | impossible — `Response.ok` is true only for statuses 200–299 (Fetch Standard) | — | — |
| 4 | yes | yes | no | impossible — same invariant | — | — |
| 5 | no | yes | yes | real | sign-in view plus `Sesja wygasła…` | FE-03 |
| 6 | no | yes | no | real | throws `detail`; the sign-in error is shown | FE-09 |
| 7 | no | no | yes | real | throws `detail`; the message is shown and the view stays | FE-06 |
| 8 | no | no | no | real | throws `detail`; the message is shown on the sign-in view | FE-01 |

For rows 6–8 the message depends on the shape of `detail` (frontend/app.js:103-110):

| # | `detail` is a string | `detail` is an array | Classification | Message | Scenario |
|---|---|---|---|---|---|
| 1 | yes | yes | impossible — one JSON value has one type | — | — |
| 2 | yes | no | real | the string | FE-06, FE-09 |
| 3 | no | yes | real | the `msg` values joined with `; ` | FE-01 |
| 4 | no | no | real | `Błąd serwera (HTTP <status>)` | out of harness scope — no UI action reaches an API error without a JSON `detail`: the field limits keep request bodies far below 64 KiB and the patched API has no reachable 500 |

### FE-01: Sign-up shows the API's validation errors as text and creates an employee
- **Area:** registration form `#register-form` and `api()` error text — response matrix row 8, detail row 3
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is visible, click "Wyloguj".
- **Steps:**
  1. In "Rejestracja" fill Login `qa+$QA_TAG-owner@test.local`, Imię i nazwisko `QA Owner $QA_TAG`, Dział `QA` and Hasło `qa+$QA_TAG-owner@test.local-x` (it contains the login and passes the 15-character HTML minimum)
  2. Click "Zarejestruj konto"
  3. Replace Hasło with `$QA_NEW_PASSWORD`, keep the other fields, click "Zarejestruj konto" and record the owner account immediately (the UI shows no id)
- **Expected:** After step 2 `#message` shows, in the error style, text containing `Password must not contain the username` (exact text — brittle) and no JSON punctuation such as `{"detail"` or `"loc"` (frontend/app.js:107-109) (backend/app/security.py:45-46); after step 3 it shows "Konto utworzone — możesz się zalogować" in the success style and every "Rejestracja" field is empty (frontend/app.js:375-376)
- **Edge cases:**
  - Reload `/` so that `#message` starts empty, fill Login `qa+$QA_TAG-short@test.local` and Imię i nazwisko `QA Short $QA_TAG`, type Hasło `Krotkie-Has-14` (14 characters) with the keyboard, then click "Zarejestruj konto": no account is created and "Konto utworzone — możesz się zalogować" does not appear — the browser blocks the submit (the Hasło input reports `validity.tooShort` and `#message` stays empty) (frontend/index.html:54)
  - Register Login `qa+$QA_TAG-owner@test.local` again (Imię i nazwisko `QA Owner $QA_TAG`, Hasło `$QA_NEW_PASSWORD`): `#message` shows `Username is already taken` in the error style (backend/app/routers/auth.py:56-62)
  - Login `qa $QA_TAG spacja` (with spaces), Imię i nazwisko `QA Spacja $QA_TAG`, Hasło `$QA_NEW_PASSWORD`: `#message` shows text containing `String should match pattern` (exact text — brittle) in the error style, and "Konto utworzone — możesz się zalogować" does not appear (backend/app/schemas.py:9) (backend/app/schemas.py:21)

### FE-02: Sign-in keeps the session cookie away from page scripts; sign-out ends it and resets the view
- **Area:** `#login-form`, user bar, `#logout-button`, `showAuthView` — response matrix row 2
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is visible, click "Wyloguj". Unless this dispatch already registered owner, register it through "Rejestracja" (Login `qa+$QA_TAG-owner@test.local`, Imię i nazwisko `QA Owner $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account.
- **Steps:**
  1. In "Logowanie" fill Login `qa+$QA_TAG-owner@test.local` and Hasło `$QA_NEW_PASSWORD`, then click "Zaloguj"
  2. Wait for `Zalogowano:`; evaluate `/(?:^|;\s*)session=/.test(document.cookie)` in the page, never `document.cookie` itself
  3. In "Nowe zgłoszenie" type `Niedokończone fe02 $QA_TAG` into Tytuł, and in "Zgłoszenia" type `fe02 $QA_TAG` into Szukaj, without submitting either form
  4. Click "Wyloguj"
- **Expected:** After step 2 `#user-info` reads "Zalogowano: QA Owner $QA_TAG (pracownik)", both "Logowanie" fields are empty, and the expression returns `false` because the `session` cookie is `HttpOnly` (backend/app/routers/auth.py:132-140) (frontend/app.js:352-356); after step 4 `#message` shows "Wylogowano" in the success style, the sign-in view is visible, the app view and the user bar are hidden, and the Tytuł and Szukaj inputs are empty (frontend/app.js:128-143) (frontend/app.js:391-392)
- **Edge cases:**
  - Right after step 4, `#ticket-list` has no rows and `#ticket-detail` is empty and hidden, so no data of the signed-out user stays in the page (frontend/app.js:135-138)
  - Still signed out, run `fetch('http://localhost:8000/api/auth/me', {credentials: 'include'})` in the page: its status is `401`; reloading then shows the sign-in view — the server ended the session and the cookie was deleted (backend/app/routers/auth.py:150-158)
  - Sign in again with Login `qa+$QA_TAG-owner@test.local` and Hasło `$QA_NEW_PASSWORD`, then reload the page: the app view and "Zalogowano: QA Owner $QA_TAG (pracownik)" return without signing in again, because the start-up `GET /api/auth/me` still authenticates with the HttpOnly cookie (frontend/app.js:429-441)

### FE-03: A session ended outside the page sends the next action back to sign-in
- **Area:** `api()` 401 handling — response matrix row 5
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is visible, click "Wyloguj". Unless this dispatch already registered owner, register it through "Rejestracja" (Login `qa+$QA_TAG-owner@test.local`, Imię i nazwisko `QA Owner $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account. Sign in through "Logowanie" with Login `qa+$QA_TAG-owner@test.local` and Hasło `$QA_NEW_PASSWORD`, and wait for `Zalogowano:`.
- **Steps:**
  1. In the page run `(await fetch('http://localhost:8000/api/auth/logout', {method: 'POST', credentials: 'include'})).status` and note it (`200`): the server ends the session while the page still shows the app view
  2. Click "Filtruj"
- **Expected:** The sign-in view is shown, the app view and the user bar are hidden, and `#message` shows "Sesja wygasła lub została zakończona — zaloguj się ponownie." in the error style (frontend/app.js:98-101) (frontend/app.js:3)
- **Edge cases:**
  - Right after the main flow, sign in through "Logowanie" again (Login `qa+$QA_TAG-owner@test.local`, Hasło `$QA_NEW_PASSWORD`): the app view returns and `#message` is cleared (frontend/app.js:352-356)
  - Signed in again, repeat step 1, then fill Tytuł `Po wylogowaniu fe03 $QA_TAG` and Opis `Nie powinno powstać.` and click "Wyślij zgłoszenie": the same message and sign-in view appear; after signing in again, Szukaj `fe03 $QA_TAG` and "Filtruj" show only "Brak zgłoszeń." — the refused request created nothing (frontend/app.js:98-101) (backend/app/dependencies.py:36-38)

### FE-04: Names and ticket data from the API render as plain text
- **Area:** `#user-info`, `#ticket-list` and `#ticket-detail` rendering through `el()` and `textContent`
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is visible, click "Wyloguj". Unless this dispatch already registered xss, register it through "Rejestracja" with Login `qa+$QA_TAG-xss@test.local`, Imię i nazwisko `<img src=x onerror="document.title='XSS-name'">`, Dział `QA` and Hasło `$QA_NEW_PASSWORD`, and record the account. Sign in with Login `qa+$QA_TAG-xss@test.local` and Hasło `$QA_NEW_PASSWORD`.
- **Steps:**
  1. In "Nowe zgłoszenie" fill Tytuł `XSS fe04 $QA_TAG <img src=x onerror="document.title='XSS'">`, choose Kategoria "Inne", fill Nr inwentarzowy `<b>AT-fe04</b>`, Lokalizacja `<svg onload="document.title='XSS-loc'">` and Opis `<script>document.title='XSS-desc'</script><i>opis</i>`, then click "Wyślij zgłoszenie"
  2. Click the new row, type `<img src=x onerror="document.title='XSS-comment'">` into "Nowy komentarz" and click "Dodaj komentarz"
  3. Click "Wyloguj", then sign in with Login `$QA_AGENT_EMAIL` and Hasło `$QA_AGENT_PASSWORD`
  4. Fill Szukaj `fe04 $QA_TAG`, click "Filtruj", then click the row
- **Expected:** In the agent's list the Tytuł cell shows the typed title literally, `<img …>` included, and Zgłaszający shows `<img src=x onerror="document.title='XSS-name'">` as text; the detail panel shows Nr inwentarzowy, Lokalizacja, Opis and the comment with its author name as the literal typed strings; `document.querySelectorAll('#ticket-list img, #ticket-list svg, #ticket-detail img, #ticket-detail svg, #ticket-detail script, #ticket-detail b, #ticket-detail i').length` is `0`, and `document.title` is still "PatchPoint — Helpdesk IT" (frontend/app.js:161-173) (frontend/app.js:245-283) (frontend/index.html:6)
- **Edge cases:**
  - Click "Wyloguj" and sign in as xss again (Login `qa+$QA_TAG-xss@test.local`, Hasło `$QA_NEW_PASSWORD`): `#user-info` reads `Zalogowano: <img src=x onerror="document.title='XSS-name'"> (pracownik)` and has no element children (frontend/app.js:149)
  - Still signed in as xss, fill Szukaj `fe04 $QA_TAG`, click "Filtruj" and open the row: the own list row and detail panel show the same literal strings, the selector count above is `0` and `document.title` is unchanged (frontend/app.js:241-286)
  - Click "Wyloguj", sign in with Login `$QA_AGENT_EMAIL` and Hasło `$QA_AGENT_PASSWORD`, fill Szukaj `fe04 $QA_TAG`, click "Filtruj", open the row and click "Przypisz do mnie": once the panel and the list re-render, the selector count is still `0`, the title is still literal text and `document.title` is unchanged (frontend/app.js:288-291) (frontend/app.js:319-330)

### FE-05: Agent assigns, changes the status and comments in the detail panel
- **Area:** agent actions "Przypisz do mnie", status select, "Zmień status" and the comment form — response matrix row 1
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is visible, click "Wyloguj". Unless this dispatch already registered owner, register it through "Rejestracja" (Login `qa+$QA_TAG-owner@test.local`, Imię i nazwisko `QA Owner $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account. Sign in as owner (Login `qa+$QA_TAG-owner@test.local`, Hasło `$QA_NEW_PASSWORD`), file Tytuł `Monitor fe05 $QA_TAG`, Kategoria "Monitor", Opis `Brak obrazu po podłączeniu.` through "Nowe zgłoszenie", click "Wyloguj", sign in with Login `$QA_AGENT_EMAIL` and Hasło `$QA_AGENT_PASSWORD`, fill Szukaj `fe05 $QA_TAG`, click "Filtruj" and click the row.
- **Steps:**
  1. Click "Przypisz do mnie"
  2. Choose "W realizacji" in the status select and click "Zmień status"
  3. Type `Diagnoza w toku fe05 $QA_TAG` into "Nowy komentarz" and click "Dodaj komentarz"
- **Expected:** Step 1 shows "Zgłoszenie przypisane do Ciebie" and the panel's "Przypisany:" shows the agent's full name from `#user-info`; step 2 shows "Status zmieniony" and the badge "W realizacji"; step 3 shows "Komentarz dodany" and the comment under the agent's full name; the refreshed list row shows "W realizacji" and the agent's name under Przypisany (frontend/app.js:319-330) (frontend/app.js:308-317) (frontend/app.js:293-306) (frontend/app.js:288-291)
- **Edge cases:**
  - After step 3 the status select offers exactly "Otwarte", "W realizacji", "Rozwiązane" and "Zamknięte", with the ticket's current status "W realizacji" selected (frontend/app.js:208-210)
  - Click "Dodaj komentarz" with "Nowy komentarz" empty: the required-field check blocks the submit, no new comment appears and `#message` keeps its text (frontend/app.js:229)
  - Click "Wyloguj", sign in as owner, fill Szukaj `fe05 $QA_TAG`, click "Filtruj" and open the ticket: the panel shows "W realizacji", the agent's name and the agent's comment, and has no status select, "Zmień status" or "Przypisz do mnie" (frontend/app.js:204-207)

### FE-06: Agent sees a refused status change as text and keeps working
- **Area:** status change error path — response matrix row 7, detail row 2
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is visible, click "Wyloguj". Unless this dispatch already registered owner, register it through "Rejestracja" (Login `qa+$QA_TAG-owner@test.local`, Imię i nazwisko `QA Owner $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account. Sign in as owner, file Tytuł `Skaner fe06 $QA_TAG`, Kategoria "Urządzenie peryferyjne", Opis `Nie skanuje dokumentów.` through "Nowe zgłoszenie", click "Wyloguj", sign in with Login `$QA_AGENT_EMAIL` and Hasło `$QA_AGENT_PASSWORD`, fill Szukaj `fe06 $QA_TAG`, click "Filtruj" and click the row (status "Otwarte").
- **Steps:**
  1. Choose "Rozwiązane" in the status select and click "Zmień status"
- **Expected:** `#message` shows `Invalid status transition: open -> resolved` in the error style; the badge stays "Otwarte", the panel stays open and the user bar stays visible (backend/app/routers/tickets.py:182-190) (frontend/app.js:103-106) (frontend/app.js:314-316)
- **Edge cases:**
  - Then choose "W realizacji" and click "Zmień status": "Status zmieniony" and the badge "W realizacji" — the error left the panel usable (backend/app/routers/tickets.py:26)
  - Then choose "Zamknięte" and click "Zmień status": `Invalid status transition: in_progress -> closed` in the error style, and the badge stays "W realizacji" (backend/app/routers/tickets.py:27)

### FE-07: Select lists come from the label maps; field limits and pagination controls
- **Area:** `#ticket-form`, `#filter-form`, `.pagination`, `loadTickets`
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is visible, click "Wyloguj". Unless this dispatch already registered owner, register it through "Rejestracja" (Login `qa+$QA_TAG-owner@test.local`, Imię i nazwisko `QA Owner $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account. Sign in as owner (Login `qa+$QA_TAG-owner@test.local`, Hasło `$QA_NEW_PASSWORD`); choose Status "Wszystkie", clear Szukaj and click "Filtruj".
- **Steps:**
  1. Read the options (value and label) of "Nowe zgłoszenie" Kategoria and Priorytet and of the "Zgłoszenia" Status filter
  2. Fill Tytuł `Drukarka fe07 $QA_TAG`, choose Kategoria "Drukarka" and Priorytet "Wysoki", fill Opis `Test list wyboru.` and click "Wyślij zgłoszenie"
  3. Read "Poprzednia", "Następna", `#page-info` and the URL of the latest `/api/tickets?` entry in `performance.getEntriesByType('resource')`
- **Expected:** Kategoria lists laptop "Laptop", desktop "Komputer stacjonarny", monitor "Monitor", printer "Drukarka", peripheral "Urządzenie peryferyjne", network "Sieć", other "Inne"; Priorytet lists low "Niski", medium "Średni" (selected), high "Wysoki", critical "Krytyczny"; Status lists "" "Wszystkie", open "Otwarte", in_progress "W realizacji", resolved "Rozwiązane", closed "Zamknięte" (frontend/app.js:5-27) (frontend/app.js:71-80); after step 2 `#message` shows "Zgłoszenie wysłane", the form is back to Kategoria "Laptop" and Priorytet "Średni", and the new row shows "Drukarka", "Wysoki" and "Otwarte" (frontend/app.js:410-413); "Poprzednia" and "Następna" are disabled, `#page-info` reads "Strona 1" and the request URL contains `limit=50` and `offset=0` (frontend/app.js:193-202)
- **Edge cases:**
  - The inputs report these limits: "Logowanie" Login `maxLength` 50 and Hasło 128; "Rejestracja" Login `minLength` 3 and `maxLength` 50, Imię i nazwisko 100, Dział 100, Hasło required with `minLength` 15 and `maxLength` 128; Tytuł 200, Nr inwentarzowy 50, Lokalizacja 100, Opis 5000; Szukaj 100; typing 201 characters into Tytuł leaves 200 (frontend/index.html:34-96)
  - Choose Status "Zamknięte" and click "Filtruj": the table holds one row "Brak zgłoszeń." whose cell spans 8 columns, and the request URL contains `status=closed`, `limit=50` and `offset=0` (frontend/app.js:154-157) (frontend/app.js:182-197)

### FE-08: The Content Security Policy is loaded and enforced
- **Area:** `<head>` meta tags of `frontend/index.html`
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is visible, click "Wyloguj"; then wait for "Logowanie". The steps run as an anonymous visitor.
- **Steps:**
  1. Read the `content` of `meta[http-equiv="Content-Security-Policy"]` and of `meta[name="referrer"]`
  2. In the page run `window.__qaCsp = []; document.addEventListener('securitypolicyviolation', (e) => window.__qaCsp.push(e.effectiveDirective));`
  3. In the page run `(await fetch('http://localhost:8000/api/health')).status`, then read the number of options in "Nowe zgłoszenie" Kategoria and `getComputedStyle(document.querySelector('.pagination')).display`
- **Expected:** The CSP content is exactly `default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src http://localhost:8000; base-uri 'none'; form-action 'none'` and the referrer content is `no-referrer` (frontend/index.html:7-8); the fetch returns `200` and `window.__qaCsp` stays empty; Kategoria has 7 options, so `app.js` ran under `script-src 'self'` (frontend/app.js:78-80); `.pagination` computes `display` `flex`, so `styles.css` loaded under `style-src 'self'` (frontend/styles.css:140-145)
- **Edge cases:**
  - Run `fetch('/')` (the UI's own origin, absent from `connect-src`): it rejects with a `TypeError` and `window.__qaCsp` gains `connect-src` (frontend/index.html:7)
  - Run `const s = document.createElement('script'); s.textContent = 'window.__qaInline = 1'; document.head.append(s);`: `window.__qaInline` stays undefined and `window.__qaCsp` gains an entry starting with `script-src` (frontend/index.html:7)
  - Run `document.body.insertAdjacentHTML('beforeend', '<img src="/qa-missing.png" onerror="window.__qaHandler = 1">')` and wait one second: `window.__qaHandler` stays undefined — injected inline handlers do not run (frontend/index.html:7)

### FE-09: Failed sign-ins show one message, and the sixth attempt is locked out
- **Area:** `#login-form` errors — response matrix row 6, detail row 2
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is visible, click "Wyloguj". Unless this dispatch already registered locked, register it through "Rejestracja" (Login `qa+$QA_TAG-locked@test.local`, Imię i nazwisko `QA Locked $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account. Unless this dispatch already registered owner, register it the same way (Login `qa+$QA_TAG-owner@test.local`, Imię i nazwisko `QA Owner $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account.
- **Steps:**
  1. In "Logowanie" fill Login `qa+$QA_TAG-locked@test.local` and Hasło `Zle-Haslo-fe09-2026`, then click "Zaloguj"
- **Expected:** `#message` shows `Invalid username or password` in the error style and the app view stays hidden (backend/app/routers/auth.py:119-128) (frontend/app.js:104-106)
- **Edge cases:**
  - Login `qa+$QA_TAG-nobody@test.local` with Hasło `Zle-Haslo-fe09-2026`: the same `Invalid username or password` (backend/app/routers/auth.py:107-117)
  - Submit Login `qa+$QA_TAG-locked@test.local` with Hasło `Zle-Haslo-fe09-2026` four more times (five failures together with step 1), then with Hasło `$QA_NEW_PASSWORD`: `#message` shows `Too many failed login attempts. Try again later.` in the error style and the app view stays hidden although the password is correct (backend/app/routers/auth.py:91-99)
  - After that lockout, sign in with Login `qa+$QA_TAG-owner@test.local` and Hasło `$QA_NEW_PASSWORD`: the app view opens with "Zalogowano: QA Owner $QA_TAG (pracownik)" — the lock applies to one username (backend/app/sessions.py:104-111)

### FE-10: A list longer than one page moves between pages with "Następna" and "Poprzednia"
- **Area:** `.pagination` ("Poprzednia", "Następna", `#page-info`), `changePage` and `loadTickets` once the list exceeds one page
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is visible, click "Wyloguj". Unless this dispatch already registered pager, register it through "Rejestracja" (Login `qa+$QA_TAG-pager@test.local`, Imię i nazwisko `QA Pager $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account. Sign in with Login `qa+$QA_TAG-pager@test.local` and Hasło `$QA_NEW_PASSWORD`, leaving Status "Wszystkie" and Szukaj empty. Then, for NN = 01, 02, …, 51 in this order, file a ticket through "Nowe zgłoszenie": fill Tytuł `Strona fe10-NN $QA_TAG` and Opis `Paginacja fe10.`, keep the default Kategoria and Priorytet, click "Wyślij zgłoszenie" and wait until the first row of `#ticket-list` shows that title. Pager files nothing else, so its list holds exactly these 51 tickets.
- **Steps:**
  1. Read whether "Poprzednia" and "Następna" are enabled, `#page-info`, the number of rows in `#ticket-list` and the Tytuł of its first and last row
  2. Click "Następna"; read the same, plus the URL of the latest `/api/tickets?` entry in `performance.getEntriesByType('resource')`
  3. Click "Poprzednia"; read the same as in step 2
- **Expected:** After step 1 `#page-info` reads "Strona 1", `#ticket-list` has 50 rows from `Strona fe10-51 $QA_TAG` down to `Strona fe10-02 $QA_TAG`, "Poprzednia" is disabled and "Następna" is enabled — a full page of 50 rows may have a successor (frontend/app.js:2) (frontend/app.js:199-201) (backend/app/routers/tickets.py:55); after step 2 `#page-info` reads "Strona 2", the only row is `Strona fe10-01 $QA_TAG`, "Poprzednia" is enabled, "Następna" is disabled and the request URL contains `limit=50` and `offset=50` (frontend/app.js:332-342) (frontend/app.js:193-202); after step 3 `#page-info` reads "Strona 1", the 50 rows of step 1 are back, "Poprzednia" is disabled, "Następna" is enabled and the request URL contains `offset=0` (frontend/app.js:332-342)
- **Edge cases:**
  - Click "Następna", then fill Szukaj `fe10-5` and click "Filtruj": `#page-info` reads "Strona 1", the list shows exactly two rows, `Strona fe10-51 $QA_TAG` then `Strona fe10-50 $QA_TAG`, both buttons are disabled and the request URL contains `search=fe10-5` and `offset=0` — a new filter starts from the first page (frontend/app.js:419-427) (frontend/app.js:182-191)
  - Clear Szukaj, click "Filtruj" and then "Następna" ("Strona 2"); click "Wyloguj" and sign in again with Login `qa+$QA_TAG-pager@test.local` and Hasło `$QA_NEW_PASSWORD`: `#page-info` reads "Strona 1", the first row is `Strona fe10-51 $QA_TAG` and "Poprzednia" is disabled (frontend/app.js:131) (frontend/app.js:352-353)
  - Click "Następna" ("Strona 2"), then file Tytuł `Strona fe10-52 $QA_TAG` with Opis `Paginacja fe10.` through "Nowe zgłoszenie": `#message` shows "Zgłoszenie wysłane", `#page-info` reads "Strona 1", the first row is `Strona fe10-52 $QA_TAG` and "Poprzednia" is disabled (frontend/app.js:410-413) (frontend/app.js:199-201)

## BE Test Scenarios

Sessions travel only in the `session` cookie: retain it from each login's `Set-Cookie` (qa-redact masks the value) and send it back as a `Cookie` header. A scenario registers owner, other, locked, retry or leaver only if this dispatch has not done so yet. Letters such as T, F, A and C name the `id` values retained from the scenario's own ticket-creation requests. `9223372036854775807` (2⁶³−1) is the largest valid ticket id and is never reached by real tickets.

### BE-01: Health reports only its status and carries the API security headers
- **Area:** `GET /api/health`, `SecurityHeadersMiddleware`
- **Target:** backend
- **Writes:** no
- **Preconditions:** none; anonymous requests without a cookie
- **Method:** GET /api/health
- **Headers:** none
- **Payload:** none
- **Expected:** `200`; the body is exactly `{"status": "ok"}`, with `status` as its only key (backend/app/routers/health.py:10-14); the headers include `x-content-type-options: nosniff`, `x-frame-options: DENY`, `referrer-policy: no-referrer`, `content-security-policy: default-src 'none'; frame-ancestors 'none'` and `cache-control: no-store` (backend/app/middleware.py:6-16)
- **Edge cases:**
  - `GET /api/auth/me` without a cookie: `401` `{"detail": "Not authenticated"}` carrying the same five headers — the middleware also wraps error responses (backend/app/middleware.py:28-37)
  - `GET /` (no route, outside `/api/`): `404` with `x-content-type-options: nosniff`, `x-frame-options: DENY` and `referrer-policy: no-referrer`, but without `content-security-policy` and `cache-control` (backend/app/middleware.py:28) (backend/app/middleware.py:35-37)

### BE-02: API documentation is not exposed
- **Area:** `docs_url`, `redoc_url` and `openapi_url`, off by default
- **Target:** backend
- **Writes:** no
- **Preconditions:** none; anonymous requests
- **Method:** GET /docs
- **Headers:** none
- **Payload:** none
- **Expected:** `404` `{"detail": "Not Found"}` (backend/app/main.py:55-65) (backend/app/config.py:17)
- **Edge cases:**
  - `GET /redoc`: `404` `{"detail": "Not Found"}` (backend/app/main.py:56)
  - `GET /openapi.json`: `404` `{"detail": "Not Found"}` (backend/app/main.py:57)

### State combinations — CORS (BE-03…BE-08)

`CORSMiddleware` (backend/app/main.py:71-78) answers from three inputs: whether `Origin` is on the allow-list, which holds only `http://localhost:5500` (backend/app/config.py:18); whether the request is a preflight, i.e. `OPTIONS` with `Origin` and `Access-Control-Request-Method` (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:86-89); and whether the requested method and headers are allowed — GET/POST/PATCH, `Content-Type` and the safelisted headers (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:119-130).

| # | Origin allowed | Preflight | Requested method and headers allowed | Classification | Outcome | Scenario |
|---|---|---|---|---|---|---|
| 1 | yes | yes | yes | real | `200`, the origin echoed with credentials | BE-03 |
| 2 | yes | yes | no | real | `400` | BE-04 |
| 3 | no | yes | yes | real | `400` without `access-control-allow-origin` | BE-05 |
| 4 | no | yes | no | real | `400` without `access-control-allow-origin` | BE-06 |
| 5 | yes | no | yes | real — a simple request asks for nothing, so nothing is disallowed | the app's response plus the origin and credentials headers | BE-07 |
| 6 | yes | no | no | impossible — only a preflight carries `Access-Control-Request-*` headers to evaluate; every other request skips that check (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:86-91) | — | — |
| 7 | no | no | yes | real | the app's response without `access-control-allow-origin` | BE-08 |
| 8 | no | no | no | impossible — same invariant as row 6 | — | — |

### BE-03: Preflight from the UI origin is allowed with credentials
- **Area:** CORS preflight — matrix row 1
- **Target:** backend
- **Writes:** no
- **Preconditions:** none; anonymous `OPTIONS` requests, which change no state
- **Method:** OPTIONS /api/tickets
- **Headers:** `Origin: http://localhost:5500`, `Access-Control-Request-Method: GET`, `Access-Control-Request-Headers: content-type`
- **Payload:** none
- **Expected:** `200`; `access-control-allow-origin: http://localhost:5500`, `access-control-allow-credentials: true`, `access-control-allow-methods: GET, POST, PATCH`, `access-control-allow-headers: Accept, Accept-Language, Content-Language, Content-Type` (no `Authorization`) and `access-control-max-age: 600`; the plain-text body is withheld by qa-redact and not asserted (backend/app/main.py:71-78) (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:47-62)
- **Edge cases:**
  - The same headers with `Access-Control-Request-Method: PATCH` (the agent's status and assignment calls): `200` with the same `access-control-allow-origin` (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:119-120)
  - `OPTIONS /api/auth/login` with `Origin: http://localhost:5500`, `Access-Control-Request-Method: POST` and `Access-Control-Request-Headers: content-type`: `200` with `access-control-allow-origin: http://localhost:5500` (backend/app/main.py:75-76)

### BE-04: Preflight from the UI origin asking for a forbidden header or method is refused
- **Area:** CORS preflight — matrix row 2
- **Target:** backend
- **Writes:** no
- **Preconditions:** none; anonymous `OPTIONS` requests, which change no state
- **Method:** OPTIONS /api/auth/me
- **Headers:** `Origin: http://localhost:5500`, `Access-Control-Request-Method: GET`, `Access-Control-Request-Headers: authorization`
- **Payload:** none
- **Expected:** `400` — a cross-origin page cannot send an `Authorization` header (backend/app/main.py:76) (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:126-130)
- **Edge cases:**
  - `Access-Control-Request-Method: DELETE` without `Access-Control-Request-Headers`: `400` (backend/app/main.py:75) (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:119-120)
  - `Access-Control-Request-Headers: content-type, authorization`: `400` — one disallowed header refuses the whole preflight (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:126-130)

### BE-05: Preflight from a foreign origin is refused without an allow-origin header
- **Area:** CORS preflight — matrix row 3
- **Target:** backend
- **Writes:** no
- **Preconditions:** none; anonymous `OPTIONS` requests, which change no state
- **Method:** OPTIONS /api/tickets
- **Headers:** `Origin` built from the scheme `http`, the separator `://` and the host `evil.example`; `Access-Control-Request-Method: GET`
- **Payload:** none
- **Expected:** `400` and no `access-control-allow-origin` header (backend/app/config.py:18) (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:111-117)
- **Edge cases:**
  - `Origin: http://localhost:8000` (the API's own origin, not on the allow-list): `400` and no `access-control-allow-origin` (backend/app/config.py:18)
  - `Origin` built from the scheme `http`, `://`, the host `127.0.0.1` and the port `5500` (the UI reached by IP): `400` and no `access-control-allow-origin` — the allow-list compares exact strings (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:93-100)
  - `Origin: null` (an opaque origin): `400` and no `access-control-allow-origin` (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:93-100)

### BE-06: Foreign-origin preflight asking for a forbidden header is refused
- **Area:** CORS preflight — matrix row 4
- **Target:** backend
- **Writes:** no
- **Preconditions:** none; anonymous `OPTIONS` requests, which change no state
- **Method:** OPTIONS /api/auth/me
- **Headers:** `Origin` built from the scheme `http`, `://` and the host `evil.example`; `Access-Control-Request-Method: GET`; `Access-Control-Request-Headers: authorization`
- **Payload:** none
- **Expected:** `400` and no `access-control-allow-origin` header (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:111-143)
- **Edge cases:**
  - The same `Origin` with `Access-Control-Request-Method: DELETE` and no requested headers: `400` and no `access-control-allow-origin` (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:116-120)
  - `Origin: http://localhost:8000` with `Access-Control-Request-Method: GET` and `Access-Control-Request-Headers: authorization`: `400` and no `access-control-allow-origin` (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:111-130)

### BE-07: Simple requests from the UI origin carry the allow-origin and credentials headers
- **Area:** CORS on simple responses — matrix row 5
- **Target:** backend
- **Writes:** no
- **Preconditions:** none; anonymous GET requests
- **Method:** GET /api/health
- **Headers:** `Origin: http://localhost:5500`
- **Payload:** none
- **Expected:** `200` `{"status": "ok"}` with `access-control-allow-origin: http://localhost:5500`, `access-control-allow-credentials: true` and `Origin` in `vary` (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:158-168)
- **Edge cases:**
  - `GET /api/auth/me` with the same `Origin` and no cookie: `401` `{"detail": "Not authenticated"}` still carrying `access-control-allow-origin: http://localhost:5500` and `access-control-allow-credentials: true`, so the client can read it at start-up (frontend/app.js:429-434) (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:158-168)
  - `GET /` with the same `Origin`: `404` with `access-control-allow-origin: http://localhost:5500` — CORS is the outermost middleware for every path (backend/app/main.py:68-78)

### BE-08: Simple requests from a foreign origin get no allow-origin header
- **Area:** CORS on simple responses — matrix row 7
- **Target:** backend
- **Writes:** no
- **Preconditions:** none; anonymous GET requests
- **Method:** GET /api/health
- **Headers:** `Origin` built from the scheme `http`, `://` and the host `evil.example`
- **Payload:** none
- **Expected:** `200` `{"status": "ok"}` without an `access-control-allow-origin` header, so a browser keeps the response from the foreign page (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:158-170)
- **Edge cases:**
  - `Origin: http://localhost:8000`: `200` without `access-control-allow-origin` (backend/app/config.py:18)
  - `GET /api/auth/me` with the foreign `Origin` and no cookie: `401` without `access-control-allow-origin` (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:158-170)

### BE-09: Request bodies above 64 KiB are refused before authentication
- **Area:** `RequestBodyLimitMiddleware` with `max_body_bytes` 65,536
- **Target:** backend
- **Writes:** yes
- **Preconditions:** none; anonymous requests. Each body is the letter `x` repeated to the stated size, sent with `Content-Type: application/json` and its `Content-Length`; none of them can create an account or a ticket.
- **Method:** POST /api/auth/register
- **Headers:** `Content-Type: application/json`, `Origin: http://localhost:5500`
- **Payload:** 70,000 bytes of `x`
- **Expected:** `413` with `access-control-allow-origin: http://localhost:5500` and `x-content-type-options: nosniff` — CORS and the security headers wrap the refusal; the plain-text body is withheld by qa-redact and not asserted (backend/app/main.py:68-78) (backend/.venv/lib/python3.14/site-packages/starlette/middleware/body_limit.py:115-121)
- **Edge cases:**
  - 65,537 bytes of `x`: `413` (backend/app/config.py:19) (backend/.venv/lib/python3.14/site-packages/starlette/middleware/body_limit.py:104-106)
  - Exactly 65,536 bytes of `x`: `422` with `detail[0].type` `json_invalid` — a body at the limit is read and parsed (backend/.venv/lib/python3.14/site-packages/starlette/middleware/body_limit.py:108-112) (backend/.venv/lib/python3.14/site-packages/fastapi/routing.py:476-491)
  - `POST /api/tickets` without a cookie and with 70,000 bytes of `x`: `413`, not `401` — the body is read before the session dependency runs (backend/.venv/lib/python3.14/site-packages/fastapi/routing.py:458) (backend/.venv/lib/python3.14/site-packages/fastapi/routing.py:511)

### BE-10: Sign-up creates an employee with an Argon2id password hash
- **Area:** `POST /api/auth/register`
- **Target:** backend
- **Writes:** yes
- **Preconditions:** none. The main request registers owner: record the account and retain owner's `id` immediately after the `201`.
- **Method:** POST /api/auth/register
- **Headers:** `Content-Type: application/json`
- **Payload:** `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}`
- **Expected:** `201`; the body's keys are exactly `created_at`, `department`, `full_name`, `id`, `role` and `username`, with `role` `employee` and no `password_hash` (backend/app/routers/auth.py:64-80) (backend/app/schemas.py:35-41)
- **State Check:** patchpoint: SELECT json_object('n', COUNT(*)) FROM users WHERE username = 'qa+$QA_TAG-owner@test.local' AND role = 'employee' AND password_hash LIKE '_argon2id_%' → {"n": 1}
- **State Check:** patchpoint: SELECT json_object('version', user_version) FROM pragma_user_version → {"version": 2}
- **Edge cases:**
  - The same payload again: `409` with exactly `{"detail": "Username is already taken"}`, and the body contains none of `UNIQUE`, `constraint`, `users.` or `sqlite` (backend/app/routers/auth.py:56-62)
  - The main payload with `username` `qa+$QA_TAG-short@test.local` and `password` `Short-Pass-14!` (14 characters): `422`, `detail[0].type` `string_too_short` and `detail[0].loc` `["body", "password"]` (backend/app/schemas.py:22) (backend/app/security.py:9)
  - The main payload with `username` `qa+$QA_TAG-long@test.local` and a `password` of 129 × `A`: `422`, `detail[0].type` `string_too_long` (backend/app/schemas.py:22) (backend/app/security.py:10)
  - The main payload with `username` `qa+$QA_TAG-policy@test.local` and `password` `qa+$QA_TAG-policy@test.local-long`: `422`, `detail[0].type` `value_error` and `detail[0].msg` `Value error, Password must not contain the username` (backend/app/schemas.py:26-32) (backend/app/security.py:45-46)
  - The main payload with `username` `qa $QA_TAG owner` (with spaces): `422`, `detail[0].type` `string_pattern_mismatch` (backend/app/schemas.py:9) (backend/app/schemas.py:21)
  - The main payload with `username` `qa+$QA_TAG-name@test.local` and a `full_name` of 101 × `x`: `422`, `detail[0].type` `string_too_long` (backend/app/schemas.py:23)

### BE-11: Sign-up refuses a role field and creates no account
- **Area:** `POST /api/auth/register` — `extra="forbid"`, role always `employee`
- **Target:** backend
- **Writes:** yes
- **Preconditions:** none; `qa+$QA_TAG-escalate@test.local` is never registered.
- **Method:** POST /api/auth/register
- **Headers:** `Content-Type: application/json`
- **Payload:** `{"username": "qa+$QA_TAG-escalate@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Escalate $QA_TAG", "role": "agent"}`
- **Expected:** `422`; `detail[0].type` `extra_forbidden` and `detail[0].loc` `["body", "role"]` (backend/app/schemas.py:19)
- **State Check:** patchpoint: SELECT json_object('n', COUNT(*)) FROM users WHERE username = 'qa+$QA_TAG-escalate@test.local' → {"n": 0}
- **State Check:** patchpoint: SELECT json_object('n', COUNT(*)) FROM users WHERE username LIKE 'qa+$QA_TAG-%' AND role <> 'employee' → {"n": 0}
- **Edge cases:**
  - The payload with `"role": "employee"` instead: `422`, `detail[0].type` `extra_forbidden` — no role value is accepted (backend/app/schemas.py:19)
  - The payload without `role` but with `"is_admin": true`: `422`, `detail[0].type` `extra_forbidden` (backend/app/schemas.py:19)
  - `POST /api/auth/login` `{"username": "qa+$QA_TAG-escalate@test.local", "password": "$QA_NEW_PASSWORD"}`: `401` `{"detail": "Invalid username or password"}` — no account exists (backend/app/routers/auth.py:107-117)

### State combinations — login (BE-12…BE-17)

`login` (backend/app/routers/auth.py:83-143) depends on three inputs, checked in this order: whether the username already has five failures in the last 15 minutes, whether the account exists, and whether the password verifies.

| # | Username blocked | Account exists | Password verifies | Classification | Outcome | Scenario |
|---|---|---|---|---|---|---|
| 1 | no | yes | yes | real | `200` `{"user": …}` and the session cookie; failures cleared | BE-12 |
| 2 | no | yes | no | real | `401` `Invalid username or password`; failure recorded | BE-13 |
| 3 | no | no | no | real | the identical `401`; failure recorded | BE-14 |
| 4 | no | no | yes | impossible — an unknown username is checked only against a random dummy hash, so no password verifies (backend/app/routers/auth.py:107-108) (backend/app/security.py:14) | — | — |
| 5 | yes | yes | yes | real | `429` with `Retry-After: 900` and no session | BE-15 |
| 6 | yes | yes | no | real | the same `429` | BE-16 |
| 7 | yes | no | no | real | the same `429` — failures are counted per username, existing or not (backend/app/routers/auth.py:107-109) | BE-17 |
| 8 | yes | no | yes | impossible — same invariant as row 4 | — | — |

### BE-12: Correct credentials return only the user and a hashed, time-limited session
- **Area:** `POST /api/auth/login`, `GET /api/auth/me` — matrix row 1
- **Target:** backend
- **Writes:** yes
- **Preconditions:** Unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account and retain owner's `id`.
- **Method:** POST /api/auth/login
- **Headers:** `Content-Type: application/json`
- **Payload:** `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}`
- **Expected:** `200`; the body's only key is `user` (no `token`), and `user` has exactly the keys `created_at`, `department`, `full_name`, `id`, `role` and `username`, with `role` `employee`; the response has a `set-cookie` header (value masked) — retain the `session` cookie (backend/app/routers/auth.py:130-143) (backend/app/schemas.py:51-52)
- **State Check:** patchpoint: SELECT json_object('total', COUNT(*), 'hashed', SUM(length(s.token_hash) = 64 AND s.token_hash NOT GLOB '*[^0-9a-f]*'), 'lifetime_480', SUM(CAST(round((julianday(s.expires_at) - julianday(s.created_at)) * 1440) AS INTEGER) = 480)) FROM sessions s JOIN users u ON u.id = s.user_id WHERE u.username = 'qa+$QA_TAG-owner@test.local' → total ≥ 1, hashed = total and lifetime_480 = total
- **Edge cases:**
  - `GET /api/auth/me` with the retained cookie: `200` with the same six keys, `role` `employee` and no `password_hash` (backend/app/routers/auth.py:164-166)
  - `GET /api/auth/me` with no cookie but `Authorization: Bearer <the retained cookie's value after session=>`: `401` `{"detail": "Not authenticated"}` — only the cookie authenticates (backend/app/dependencies.py:36-38)
  - `GET /api/auth/me` with the retained cookie and `Authorization: Bearer forged`: `200` — the header is ignored (backend/app/dependencies.py:36)
  - `GET /api/auth/me` with `Cookie: session=forged`: `401` `{"detail": "Not authenticated"}` (backend/app/sessions.py:64-65) (backend/app/dependencies.py:42-50)
  - The main payload plus `"remember": true`: `422`, `detail[0].type` `extra_forbidden` (backend/app/schemas.py:45)
  - Send the main request once more and compare the two retained cookie values locally, never printing them: both values after `session=` match `^[A-Za-z0-9_-]{43,}$` and they differ (backend/app/security.py:32-33)

### BE-13: A wrong password for an existing account gets the generic 401
- **Area:** `POST /api/auth/login` — matrix row 2
- **Target:** backend
- **Writes:** yes
- **Preconditions:** Unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account and retain owner's `id`.
- **Method:** POST /api/auth/login
- **Headers:** `Content-Type: application/json`
- **Payload:** `{"username": "qa+$QA_TAG-owner@test.local", "password": "Wrong-Password-2026!"}`
- **Expected:** `401`; the body is exactly `{"detail": "Invalid username or password"}` and there is no `set-cookie` header (backend/app/routers/auth.py:119-128)
- **Edge cases:**
  - Then the main payload with `"password": "$QA_NEW_PASSWORD"`: `200` with `user` — one failure does not block, and the success clears it (backend/app/sessions.py:104-111) (backend/app/routers/auth.py:130)
  - `{"username": "qa+$QA_TAG-owner@test.local", "password": ""}`: `422`, `detail[0].type` `string_too_short` (backend/app/schemas.py:48)
  - Owner's username with a password of 129 × `A`: `422`, `detail[0].type` `string_too_long` (backend/app/schemas.py:48)

### BE-14: An unknown username gets the identical 401 and is still counted
- **Area:** `POST /api/auth/login` — matrix row 3
- **Target:** backend
- **Writes:** yes
- **Preconditions:** none; `qa+$QA_TAG-nobody@test.local` is never registered.
- **Method:** POST /api/auth/login
- **Headers:** `Content-Type: application/json`
- **Payload:** `{"username": "qa+$QA_TAG-nobody@test.local", "password": "Wrong-Password-2026!"}`
- **Expected:** `401`; the body is exactly `{"detail": "Invalid username or password"}`, the same as for a wrong password, and there is no `set-cookie` header (backend/app/routers/auth.py:107-117)
- **State Check:** patchpoint: SELECT json_object('n', COUNT(*)) FROM login_failures WHERE username = 'qa+$QA_TAG-nobody@test.local' → {"n": 1}
- **Edge cases:**
  - `{"username": "admin", "password": "admin123"}` (the Phase 1 default account): `401` with the same body — no `admin` account is seeded (backend/app/database.py:44-48); a `429` `{"detail": "Too many failed login attempts. Try again later."}` is acceptable only when `admin` already has five failures from the last 15 minutes; never `200`
  - `{"username": "$QA_AGENT_EMAIL", "password": "helpdesk123"}` (the Phase 1 demo password): `401` with the same body; then `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}`: `200` with `user.role` `agent`, which also clears this failure — demo accounts use only `PATCHPOINT_DEMO_PASSWORD` (backend/app/database.py:197-218)

### BE-15: Five failures lock the username even for the correct password
- **Area:** `POST /api/auth/login` lockout — matrix row 5
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Unless this dispatch already registered locked: POST `/api/auth/register` `{"username": "qa+$QA_TAG-locked@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Locked $QA_TAG", "department": "QA"}` (`201`); record the account.
  2. POST `/api/auth/login` `{"username": "qa+$QA_TAG-locked@test.local", "password": "Wrong-Password-2026!"}` five times; each answers `401` `{"detail": "Invalid username or password"}`.
  3. Unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account and retain owner's `id`.
- **Method:** POST /api/auth/login
- **Headers:** `Content-Type: application/json`
- **Payload:** `{"username": "qa+$QA_TAG-locked@test.local", "password": "$QA_NEW_PASSWORD"}`
- **Expected:** `429`; the body is exactly `{"detail": "Too many failed login attempts. Try again later."}`, the header `retry-after` is `900`, and there is no `set-cookie` header (backend/app/routers/auth.py:91-99) (backend/app/config.py:23-24)
- **State Check:** patchpoint: SELECT json_object('n', COUNT(*)) FROM login_failures WHERE username = 'qa+$QA_TAG-locked@test.local' → {"n": 5}
- **Edge cases:**
  - `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}`: `200` — the lock applies to one username only (backend/app/sessions.py:104-111)
  - Locked's username with a password of 129 × `A`: `422` — schema validation runs before the lockout check (backend/app/schemas.py:48)

### BE-16: A locked username stays locked for further wrong passwords
- **Area:** `POST /api/auth/login` lockout — matrix row 6
- **Target:** backend
- **Writes:** yes
- **Preconditions:** Unless this dispatch already registered locked: POST `/api/auth/register` `{"username": "qa+$QA_TAG-locked@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Locked $QA_TAG", "department": "QA"}` (`201`) and record the account. Unless locked received five wrong-password logins within the last 15 minutes, POST `/api/auth/login` `{"username": "qa+$QA_TAG-locked@test.local", "password": "Wrong-Password-2026!"}` five times (each `401`).
- **Method:** POST /api/auth/login
- **Headers:** `Content-Type: application/json`
- **Payload:** `{"username": "qa+$QA_TAG-locked@test.local", "password": "Wrong-Password-2026!"}`
- **Expected:** `429`; the body is exactly `{"detail": "Too many failed login attempts. Try again later."}` and the header `retry-after` is `900` (backend/app/routers/auth.py:91-99)
- **State Check:** patchpoint: SELECT json_object('n', COUNT(*)) FROM login_failures WHERE username = 'qa+$QA_TAG-locked@test.local' → {"n": 5}
- **Edge cases:**
  - The same request again: `429` again, not `401` (backend/app/sessions.py:104-111)
  - `{"username": "qa+$QA_TAG-free@test.local", "password": "Wrong-Password-2026!"}` (never registered, no earlier failures): `401` `{"detail": "Invalid username or password"}` (backend/app/routers/auth.py:107-117)

### BE-17: An unknown username is locked exactly like a real one
- **Area:** `POST /api/auth/login` lockout — matrix row 7
- **Target:** backend
- **Writes:** yes
- **Preconditions:** `qa+$QA_TAG-ghost@test.local` is never registered. POST `/api/auth/login` `{"username": "qa+$QA_TAG-ghost@test.local", "password": "Wrong-Password-2026!"}` five times; each answers `401` `{"detail": "Invalid username or password"}`.
- **Method:** POST /api/auth/login
- **Headers:** `Content-Type: application/json`
- **Payload:** `{"username": "qa+$QA_TAG-ghost@test.local", "password": "Wrong-Password-2026!"}`
- **Expected:** `429`; the body is exactly `{"detail": "Too many failed login attempts. Try again later."}` and the header `retry-after` is `900`, so the lockout does not reveal whether an account exists (backend/app/routers/auth.py:91-99) (backend/app/routers/auth.py:107-109)
- **State Check:** patchpoint: SELECT json_object('n', COUNT(*)) FROM login_failures WHERE username = 'qa+$QA_TAG-ghost@test.local' → {"n": 5}
- **Edge cases:**
  - The username with a trailing space, `"qa+$QA_TAG-ghost@test.local "`, and the same password: `401` — failures are keyed on the exact username (backend/app/sessions.py:104-111)
  - `{"username": "qa+$QA_TAG-ghost@test.local", "password": ""}`: `422` — validation runs before the lockout check (backend/app/schemas.py:48)

### BE-18: A successful login resets the failure count
- **Area:** `clear_login_failures` after a successful login
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Unless this dispatch already registered retry: POST `/api/auth/register` `{"username": "qa+$QA_TAG-retry@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Retry $QA_TAG", "department": "QA"}` (`201`); record the account.
  2. POST `/api/auth/login` `{"username": "qa+$QA_TAG-retry@test.local", "password": "Wrong-Password-2026!"}` four times (each `401`); then `{"username": "qa+$QA_TAG-retry@test.local", "password": "$QA_NEW_PASSWORD"}` once (`200`) and retain this `session` cookie; then the wrong-password request four more times (each `401`).
- **Method:** POST /api/auth/login
- **Headers:** `Content-Type: application/json`
- **Payload:** `{"username": "qa+$QA_TAG-retry@test.local", "password": "$QA_NEW_PASSWORD"}`
- **Expected:** `200` with `user` — eight failures fell inside 15 minutes, but the success between them cleared the first four (backend/app/routers/auth.py:130) (backend/app/sessions.py:128-130)
- **State Check:** patchpoint: SELECT json_object('n', COUNT(*)) FROM login_failures WHERE username = 'qa+$QA_TAG-retry@test.local' → {"n": 0}
- **Edge cases:**
  - Five more wrong-password logins (each `401`), then the correct password: `429` — the count restarts at zero and blocks at five (backend/app/routers/auth.py:91-99)
  - After that lockout, `GET /api/auth/me` with the cookie retained in Preconditions: `200` — the lockout refuses new logins and leaves existing sessions alone (backend/app/dependencies.py:33-41)

### BE-19: Logout ends the session on the server
- **Area:** `POST /api/auth/logout`
- **Target:** backend
- **Writes:** yes
- **Preconditions:** Unless this dispatch already registered leaver: POST `/api/auth/register` `{"username": "qa+$QA_TAG-leaver@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Leaver $QA_TAG", "department": "QA"}` (`201`); record the account. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-leaver@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`), retain the `session` cookie, and confirm `GET /api/auth/me` with it answers `200`.
- **Method:** POST /api/auth/logout
- **Headers:** `Cookie:` leaver's `session` cookie retained in Preconditions (tester-owned, not a plan token)
- **Payload:** none
- **Expected:** `200`; the body is exactly `{"message": "Logged out"}` and the response has a `set-cookie` header (value masked) (backend/app/routers/auth.py:146-161)
- **State Check:** patchpoint: SELECT json_object('n', COUNT(*)) FROM sessions s JOIN users u ON u.id = s.user_id WHERE u.username = 'qa+$QA_TAG-leaver@test.local' → {"n": 0}
- **Edge cases:**
  - `GET /api/auth/me` with the same cookie: `401` `{"detail": "Not authenticated"}` — the logged-out cookie is useless (backend/app/sessions.py:64-65)
  - `POST /api/auth/logout` without a cookie: `200` `{"message": "Logged out"}` (backend/app/routers/auth.py:150-161)
  - Log in as leaver twice (cookies A and B) and POST `/api/auth/logout` with A: `GET /api/auth/me` with B answers `200` and with A `401` — logout ends only the presented session (backend/app/routers/auth.py:150-151) (backend/app/sessions.py:88-97)

### State combinations — ticket list filters (BE-20)

`list_tickets` (backend/app/routers/tickets.py:132-153) fills one static query (backend/app/routers/tickets.py:47-58) from three independent inputs: whether the caller is an employee rather than an agent, the only two roles (backend/app/schemas.py:13-15), which binds the `reporter_id` predicate (backend/app/routers/tickets.py:145); whether `status` is sent (backend/app/routers/tickets.py:146); and whether a non-empty `search` is sent (backend/app/routers/tickets.py:147). `limit` and `offset` page every combination alike (BE-21).

| # | Caller is employee | `status` sent | `search` sent | Classification | Rows returned | Scenario |
|---|---|---|---|---|---|---|
| 1 | yes | no | no | real | the caller's own tickets, newest first | BE-22 and BE-23 (owner's `GET /api/tickets` edges), FE-07, FE-10 |
| 2 | yes | no | yes | real | own tickets whose title or description contains the term literally | BE-20 main flow and its `O'Brien`, `%`, `_` and other-user edges; FE-10 `fe10-5` edge |
| 3 | yes | yes | no | real | own tickets with that status | BE-20 owner `status=open` edge; FE-07 "Zamknięte" edge |
| 4 | yes | yes | yes | real | own tickets with that status whose title or description contains the term | BE-20 owner `status=open` and `status=closed` edges with the `be20` search |
| 5 | no | no | no | real | every reporter's tickets, newest first | BE-20 agent `limit=100` edge; BE-21 agent edge |
| 6 | no | no | yes | real | every reporter's tickets whose title or description contains the term | BE-20 agent edge with the `be20` search |
| 7 | no | yes | no | real | every reporter's tickets with that status | BE-20 agent `status=in_progress` edge |
| 8 | no | yes | yes | real | every reporter's tickets with that status whose title or description contains the term | BE-20 agent `status=open` and `status=in_progress` edges with the `be20` search |

### BE-20: Search terms match literally, and neither search nor status widens an employee's scope
- **Area:** `GET /api/tickets?search=&status=` — static `LIST_TICKETS_SQL` with `LIKE … ESCAPE '\'` — list filter matrix rows 2–8
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account and retain owner's `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
  2. Other session — unless this dispatch already registered other: POST `/api/auth/register` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Other $QA_TAG", "department": "QA"}` (`201`), record the account and retain other's `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
  3. As owner, POST `/api/tickets` `{"title": "Laptop 100% sprawny be20-$QA_TAG", "description": "Bateria trzyma cały dzień.", "category": "laptop"}`, `{"title": "Monitor snake_case be20-$QA_TAG", "description": "Złącze HDMI jest luźne.", "category": "monitor"}` and `{"title": "Drukarka O'Brien be20-$QA_TAG", "description": "Zgłasza pan O'Brien z recepcji.", "category": "printer"}` (each `201`).
  4. As other, POST `/api/tickets` `{"title": "Tajny be20-$QA_TAG", "description": "Dane innego pracownika.", "category": "other"}` (`201`).
  5. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie.
- **Method:** GET /api/tickets?search=%27%29%20OR%201%3D1%20OR%20%28%27
- **Headers:** `Cookie:` owner's `session` cookie. The query is `search=') OR 1=1 OR ('`, URL-encoded as shown; every `search` value below is sent URL-encoded too (for example with `curl -G --data-urlencode`)
- **Payload:** none
- **Expected:** `200` `[]` — the phrase is matched as text, so it neither returns every ticket nor bypasses the reporter filter (backend/app/routers/tickets.py:47-58) (backend/app/routers/tickets.py:147)
- **Edge cases:**
  - `search` = `' UNION SELECT token_hash, 1 FROM sessions --`: `200` `[]` (backend/app/routers/tickets.py:47-58)
  - `search` = `O'Brien`: `200`; the list contains `Drukarka O'Brien be20-$QA_TAG`, every element's `title` or `description` contains `O'Brien`, and no element has `reporter_name` `QA Other $QA_TAG` (backend/app/routers/tickets.py:145-147)
  - `search` = `%`: `200`; every element's `title` or `description` contains a literal `%`, and the list contains `Laptop 100% sprawny be20-$QA_TAG` but not `Monitor snake_case be20-$QA_TAG` (backend/app/routers/tickets.py:73-77)
  - `search` = `_`: `200`; every element's `title` or `description` contains a literal `_`, and the list contains `Monitor snake_case be20-$QA_TAG` but not `Laptop 100% sprawny be20-$QA_TAG` (backend/app/routers/tickets.py:73-77)
  - As other, `search` = `be20-$QA_TAG`: `200` with exactly one element, `Tajny be20-$QA_TAG` (backend/app/routers/tickets.py:145)
  - As owner, `GET /api/tickets?status=open`: `200`, non-empty, and every element has `status` `open` and `reporter_name` `QA Owner $QA_TAG`, so other's open `Tajny be20-$QA_TAG` stays out (backend/app/routers/tickets.py:145-146)
  - As owner, `GET /api/tickets?status=open&search=be20-$QA_TAG`: `200` with exactly three elements, `Drukarka O'Brien be20-$QA_TAG`, `Monitor snake_case be20-$QA_TAG` and `Laptop 100% sprawny be20-$QA_TAG`, in this order (backend/app/routers/tickets.py:50-55)
  - As owner, `GET /api/tickets?status=closed&search=be20-$QA_TAG`: `200` `[]` — the status predicate applies together with the search (backend/app/routers/tickets.py:51)
  - As agent, `GET /api/tickets?limit=100`: `200`; the list contains both `Tajny be20-$QA_TAG` and `Laptop 100% sprawny be20-$QA_TAG`, tickets of two reporters, and its `id` values strictly decrease (backend/app/routers/tickets.py:145) (backend/app/routers/tickets.py:55)
  - As agent, `GET /api/tickets?search=be20-$QA_TAG`: `200` with exactly four elements, `Tajny be20-$QA_TAG`, `Drukarka O'Brien be20-$QA_TAG`, `Monitor snake_case be20-$QA_TAG` and `Laptop 100% sprawny be20-$QA_TAG`, in this order — an agent's search covers every reporter (backend/app/routers/tickets.py:145) (backend/app/routers/tickets.py:52-55)
  - As agent, `GET /api/tickets?status=in_progress`: `200` and non-empty, since the demo data seeds `Drukarka zacina papier` as `in_progress`, and every element has `status` `in_progress` (backend/app/routers/tickets.py:146) (backend/app/database.py:62-72)
  - As agent, `GET /api/tickets?status=open&search=be20-$QA_TAG`: `200` with the same four elements in the same order; with `status=in_progress` instead: `200` `[]` (backend/app/routers/tickets.py:50-54)
  - As owner, `GET /api/tickets?status=bogus`: `422`, `detail[0].type` `enum` and `detail[0].loc` `["query", "status"]` (backend/app/routers/tickets.py:136) (backend/app/schemas.py:80-84)
  - `search` of 101 × `a`: `422` (backend/app/routers/tickets.py:137)
  - The main request without a cookie: `401` (backend/app/dependencies.py:36-38)

### BE-21: The ticket list pages with limit and offset inside fixed bounds
- **Area:** `GET /api/tickets?limit=&offset=`
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account and retain owner's `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
  2. As owner, POST `/api/tickets` three times, in this order: `{"title": "Strona 1 be21-$QA_TAG", "description": "Paginacja listy.", "category": "other"}`, then the same with `Strona 2 be21-$QA_TAG`, then with `Strona 3 be21-$QA_TAG` (each `201`).
  3. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie.
- **Method:** GET /api/tickets?search=be21-$QA_TAG&limit=2
- **Headers:** `Cookie:` owner's `session` cookie
- **Payload:** none
- **Expected:** `200` with exactly two elements, `Strona 3 be21-$QA_TAG` then `Strona 2 be21-$QA_TAG` — newest first (backend/app/routers/tickets.py:55-56) (backend/app/routers/tickets.py:138)
- **Edge cases:**
  - `GET /api/tickets?search=be21-$QA_TAG&limit=2&offset=2` as owner: `200` with exactly one element, `Strona 1 be21-$QA_TAG` (backend/app/routers/tickets.py:139)
  - `GET /api/tickets?limit=0` and `GET /api/tickets?limit=101` as owner: `422` each (backend/app/routers/tickets.py:68) (backend/app/routers/tickets.py:138)
  - `GET /api/tickets?offset=-1` as owner: `422` (backend/app/routers/tickets.py:139)
  - `GET /api/tickets?limit=100` as owner: `200` (backend/app/routers/tickets.py:138)
  - `GET /api/tickets?offset=9223372036854775807` as owner: `200` `[]`; `GET /api/tickets?offset=9223372036854775808`: `422` (backend/app/routers/tickets.py:139) (backend/app/schemas.py:10)
  - As agent, `GET /api/tickets` without parameters: `200` with at most 50 elements (backend/app/routers/tickets.py:67) (backend/app/routers/tickets.py:138)

### State combinations — ticket access (BE-22…BE-27)

`_visible_ticket` (backend/app/routers/tickets.py:80-100) is the single existence and ownership check for reading, commenting and updating; PATCH first requires the agent role (backend/app/dependencies.py:56-67), and the list limits employees to their own tickets (backend/app/routers/tickets.py:145).

| # | Caller is agent | Caller is reporter | Ticket exists | Classification | GET detail | POST comment | PATCH | In caller's list | Scenario |
|---|---|---|---|---|---|---|---|---|---|
| 1 | no | yes | yes | real | `200` | `201` | `403` | yes | BE-22 |
| 2 | no | no | yes | real | `404` | `404` | `403` | no | BE-23 |
| 3 | yes | yes | yes | real — agents may file tickets, `create_ticket` needs only a session (backend/app/routers/tickets.py:103-106) | `200` | `201` | `200` | yes | BE-24 |
| 4 | yes | no | yes | real | `200` | `201` | `200` | yes | BE-25 |
| 5 | no | no | no | real | `404` | `404` | `403` | — | BE-26 |
| 6 | yes | no | no | real | `404` | `404` | `404` | — | BE-27 |
| 7 | no | yes | no | impossible — a missing ticket has no reporter (`tickets.reporter_id` is `NOT NULL`, backend/app/schema.sql:37), and the 404 comes before the ownership test (backend/app/routers/tickets.py:84-86) | — | — | — | — | — |
| 8 | yes | yes | no | impossible — same invariant as row 7 | — | — | — | — | — |

### BE-22: An employee reads and comments on an own ticket but cannot change it
- **Area:** `GET /api/tickets/{ticket_id}`, comments, PATCH role guard — matrix row 1
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account and retain owner's `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
  2. As owner, POST `/api/tickets` `{"title": "Własne be22-$QA_TAG", "description": "Klawiatura gubi znaki.", "category": "peripheral"}` (T, `201`); note its `updated_at`.
- **Method:** GET /api/tickets/{T}
- **Headers:** `Cookie:` owner's `session` cookie
- **Payload:** none
- **Expected:** `200`; `title` `Własne be22-$QA_TAG`, `reporter_name` `QA Owner $QA_TAG`, `status` `open` and `comments` `[]` (backend/app/routers/tickets.py:156-166) (backend/app/routers/tickets.py:88)
- **Edge cases:**
  - POST `/api/tickets/{T}/comments` `{"body": "Komentarz właściciela be22-$QA_TAG"}` as owner: `201` with `author_name` `QA Owner $QA_TAG`; GET T then shows that one comment and an `updated_at` not earlier than the value noted in Preconditions (backend/app/routers/tickets.py:236-243)
  - `GET /api/tickets` as owner: contains `Własne be22-$QA_TAG` (backend/app/routers/tickets.py:145)
  - PATCH `/api/tickets/{T}` `{"status": "closed"}` as owner: `403` `{"detail": "Helpdesk agent role required"}`, and GET T still shows `status` `open` (backend/app/dependencies.py:56-67)

### BE-23: An employee gets 404 for another employee's ticket, exactly as for a missing one
- **Area:** `_visible_ticket` ownership check — matrix row 2
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account and retain owner's `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
  2. Other session — unless this dispatch already registered other: POST `/api/auth/register` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Other $QA_TAG", "department": "QA"}` (`201`), record the account and retain other's `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
  3. As other, POST `/api/tickets` `{"title": "Cudze be23-$QA_TAG", "description": "Prywatne dane działu.", "category": "laptop", "location": "Pokój 12"}` (F, `201`).
- **Method:** GET /api/tickets/{F}
- **Headers:** `Cookie:` owner's `session` cookie
- **Payload:** none
- **Expected:** `404`; the body is exactly `{"detail": "Ticket not found"}` (backend/app/routers/tickets.py:88-98)
- **Edge cases:**
  - `GET /api/tickets/9223372036854775807` as owner: `404` with a byte-identical body, so a foreign id cannot be told from a missing one (backend/app/routers/tickets.py:84-86)
  - POST `/api/tickets/{F}/comments` `{"body": "Obcy komentarz be23-$QA_TAG"}` as owner: `404`; GET F as other then shows `comments` `[]` (backend/app/routers/tickets.py:234)
  - `GET /api/tickets` as owner: does not contain `Cudze be23-$QA_TAG` (backend/app/routers/tickets.py:145)
  - PATCH `/api/tickets/{F}` `{"status": "closed"}` as owner: `403` (backend/app/dependencies.py:56-67)
  - GET F as other: `200` — the reporter still reads it (backend/app/routers/tickets.py:88)

### BE-24: An agent reads, comments on and updates an own ticket
- **Area:** agent access to a ticket the agent filed — matrix row 3
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie, `user.id` and `user.full_name`.
  2. Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account and retain owner's `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
  3. As agent, POST `/api/tickets` `{"title": "Zgłoszenie agenta be24-$QA_TAG", "description": "Wymiana tonera w serwerowni.", "category": "printer"}` (A, `201`).
- **Method:** GET /api/tickets/{A}
- **Headers:** `Cookie:` agent's `session` cookie
- **Payload:** none
- **Expected:** `200`; `reporter_name` equals the agent's `user.full_name` and `status` is `open` (backend/app/routers/tickets.py:156-166)
- **Edge cases:**
  - POST `/api/tickets/{A}/comments` `{"body": "Notatka agenta be24-$QA_TAG"}` as agent: `201` (backend/app/routers/tickets.py:226-249)
  - PATCH `/api/tickets/{A}` `{"status": "in_progress", "assignee_id": <agent's user.id>}` as agent: `200`; `status` `in_progress` and `assignee_name` equal to the agent's `user.full_name` (backend/app/routers/tickets.py:169-223)
  - `GET /api/tickets/{A}` as owner: `404` `{"detail": "Ticket not found"}` (backend/app/routers/tickets.py:88-98)
  - `GET /api/tickets` as agent: contains `Zgłoszenie agenta be24-$QA_TAG` (backend/app/routers/tickets.py:145)

### State combinations — ticket update fields (BE-25)

`update_ticket` (backend/app/routers/tickets.py:169-223) depends on three independent inputs: whether the body sends `status`, `priority` and `assignee_id`. With none of them it answers `400` `Nothing to update` before the lookup (backend/app/routers/tickets.py:177-178); a sent `status` must be a permitted transition (backend/app/routers/tickets.py:182-190) and a sent `assignee_id` must name an agent (backend/app/routers/tickets.py:192-195); only after both checks does the single `COALESCE` update write every sent field and keep the others (backend/app/routers/tickets.py:60-65) (backend/app/routers/tickets.py:199-210).

| # | `status` sent | `priority` sent | `assignee_id` sent | Classification | Outcome | Scenario |
|---|---|---|---|---|---|---|
| 1 | no | no | no | real | `400` `Nothing to update` | BE-25 `{}` edge; BE-27 |
| 2 | no | no | yes | real | assignee check, then only the assignee is written | FE-05 step 1 ("Przypisz do mnie" sends only `assignee_id`, frontend/app.js:321-324); BE-25 edge with owner's id alone (`400`) |
| 3 | no | yes | no | real | only the priority is written | BE-25 `{"priority": "high"}` edge |
| 4 | no | yes | yes | real | assignee check, then both are written; a refused assignee writes neither | BE-25 `priority` edges with the agent's id (`200`) and with owner's id (`400`) |
| 5 | yes | no | no | real | transition check, then only the status is written | FE-05 step 2 and FE-06 ("Zmień status" sends only `status`, frontend/app.js:311); BE-25 `{"status": "closed"}` edge (`400`) |
| 6 | yes | no | yes | real | both checks, then the status and the assignee are written | BE-25 main flow; BE-24 |
| 7 | yes | yes | no | real | transition check, then both are written; a refused transition writes neither | BE-25 `status` and `priority` edges `in_progress` → `closed` (`400`) and `resolved` → `closed` (`200`) |
| 8 | yes | yes | yes | real | both checks, then all three are written | BE-25 `in_progress` → `resolved` edge with `priority` and the agent's id (`200`) |

### BE-25: An agent updates an employee's ticket, keeping fields it does not send
- **Area:** `PATCH /api/tickets/{ticket_id}` — static `UPDATE_TICKET_SQL` — ticket access matrix row 4; update field matrix rows 1–8
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account and retain owner's `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie. Owner's `id` below is the value retained at owner's registration in this dispatch.
  2. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie, `user.id` and `user.full_name`.
  3. As owner, POST `/api/tickets` `{"title": "Do obsługi be25-$QA_TAG", "description": "Stacja dokująca nie ładuje.", "category": "peripheral"}` (T, `201`, `priority` `medium`).
- **Method:** PATCH /api/tickets/{T}
- **Headers:** `Content-Type: application/json`; `Cookie:` agent's `session` cookie
- **Payload:** `{"status": "in_progress", "assignee_id": <agent's user.id>}`
- **Expected:** `200`; `status` `in_progress`, `assignee_name` equal to the agent's `user.full_name`, and `priority` still `medium` (backend/app/routers/tickets.py:60-65) (backend/app/routers/tickets.py:197-223)
- **Edge cases:**
  - T `{"priority": "high"}`: `200`; `priority` `high`, while `status` stays `in_progress` and `assignee_name` stays the agent's (backend/app/routers/tickets.py:60-65)
  - T `{"status": "closed", "priority": "low"}`: `400` `{"detail": "Invalid status transition: in_progress -> closed"}`; GET T as agent then still shows `priority` `high` and `status` `in_progress` — a refused status keeps the priority sent with it from being written (backend/app/routers/tickets.py:182-190) (backend/app/routers/tickets.py:199-210)
  - T `{"status": "closed"}`: `400` `{"detail": "Invalid status transition: in_progress -> closed"}` (backend/app/routers/tickets.py:182-190)
  - T `{"assignee_id": <owner's id>}`: `400` `{"detail": "Assignee must be a helpdesk agent"}` (backend/app/routers/tickets.py:192-195)
  - T `{"priority": "low", "assignee_id": <owner's id>}`: `400` `{"detail": "Assignee must be a helpdesk agent"}`; GET T as agent then still shows `priority` `high` and `assignee_name` equal to the agent's `user.full_name` (backend/app/routers/tickets.py:192-195) (backend/app/routers/tickets.py:199-210)
  - T `{}`: `400` `{"detail": "Nothing to update"}` (backend/app/routers/tickets.py:177-178)
  - T `{"reporter_id": 1}`: `422`, `detail[0].type` `extra_forbidden` (backend/app/schemas.py:99)
  - T `{"assignee_id": 9223372036854775808}`: `422`, `detail[0].type` `less_than_equal` (backend/app/schemas.py:103)
  - T `{"priority": "critical", "assignee_id": <agent's user.id>}`: `200`; `priority` `critical`, `assignee_name` equal to the agent's `user.full_name` and `status` still `in_progress` (backend/app/routers/tickets.py:60-65)
  - POST `/api/tickets/{T}/comments` `{"body": "Odpowiedź agenta be25-$QA_TAG"}` as agent: `201`; GET T as owner then lists that comment with `author_name` equal to the agent's `user.full_name` (backend/app/routers/tickets.py:226-249)
  - After every edge above, T `{"status": "resolved", "priority": "low", "assignee_id": <agent's user.id>}`: `200`; `status` `resolved`, `priority` `low` and `assignee_name` equal to the agent's `user.full_name` — all three sent fields are written (backend/app/routers/tickets.py:27) (backend/app/routers/tickets.py:60-65)
  - Finally T `{"status": "closed", "priority": "medium"}`: `200`; `status` `closed` and `priority` `medium` — a permitted transition writes the priority sent with it (backend/app/routers/tickets.py:28) (backend/app/routers/tickets.py:60-65)

### BE-26: A missing ticket id answers 404 to an employee
- **Area:** `_visible_ticket` existence check — matrix row 5
- **Target:** backend
- **Writes:** yes
- **Preconditions:** Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account and retain owner's `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
- **Method:** GET /api/tickets/9223372036854775807
- **Headers:** `Cookie:` owner's `session` cookie
- **Payload:** none
- **Expected:** `404`; the body is exactly `{"detail": "Ticket not found"}` (backend/app/routers/tickets.py:84-86)
- **Edge cases:**
  - POST `/api/tickets/9223372036854775807/comments` `{"body": "Komentarz be26-$QA_TAG"}` as owner: `404` (backend/app/routers/tickets.py:234)
  - PATCH `/api/tickets/9223372036854775807` `{"status": "closed"}` as owner: `403` — the role dependency runs before any lookup (backend/app/dependencies.py:56-67) (backend/.venv/lib/python3.14/site-packages/fastapi/dependencies/utils.py:704)

### BE-27: A missing ticket id answers 404 to an agent
- **Area:** `_visible_ticket` existence check — matrix row 6
- **Target:** backend
- **Writes:** yes
- **Preconditions:** Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie.
- **Method:** GET /api/tickets/9223372036854775807
- **Headers:** `Cookie:` agent's `session` cookie
- **Payload:** none
- **Expected:** `404`; the body is exactly `{"detail": "Ticket not found"}` (backend/app/routers/tickets.py:84-86)
- **Edge cases:**
  - POST `/api/tickets/9223372036854775807/comments` `{"body": "Komentarz be27-$QA_TAG"}` as agent: `404` (backend/app/routers/tickets.py:234)
  - PATCH `/api/tickets/9223372036854775807` `{"priority": "low"}` as agent: `404` `{"detail": "Ticket not found"}` (backend/app/routers/tickets.py:180)
  - PATCH `/api/tickets/9223372036854775807` `{}` as agent: `400` `{"detail": "Nothing to update"}` — the empty-update check runs before the lookup (backend/app/routers/tickets.py:177-180)

### BE-28: Ticket and comment fields enforce their length limits and refuse unknown keys
- **Area:** `TicketCreate` and `CommentCreate` (`extra="forbid"`, `max_length`)
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account and retain owner's `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
  2. As owner, POST `/api/tickets` `{"title": "Komentowane be28-$QA_TAG", "description": "Cel komentarzy.", "category": "other"}` (C, `201`).
- **Method:** POST /api/tickets
- **Headers:** `Content-Type: application/json`; `Cookie:` owner's `session` cookie
- **Payload:** `{"title": …, "description": "Granica długości tytułu.", "category": "other"}`, where `title` is `Limit be28-$QA_TAG ` followed by `x` characters until the title is exactly 200 characters long
- **Expected:** `201`; the returned `title` has exactly 200 characters (backend/app/schemas.py:90)
- **Edge cases:**
  - The main payload with one more `x` in `title` (201 characters): `422`, `detail[0].type` `string_too_long` (backend/app/schemas.py:90)
  - `{"title": "Opis be28-$QA_TAG", "description": <5001 × x>, "category": "other"}`: `422`, `detail[0].type` `string_too_long` (backend/app/schemas.py:91)
  - `{"title": "Numer be28-$QA_TAG", "description": "Za długi numer.", "category": "other", "asset_tag": <51 × x>}`: `422` (backend/app/schemas.py:94)
  - `{"title": "Miejsce be28-$QA_TAG", "description": "Za długa lokalizacja.", "category": "other", "location": <101 × x>}`: `422` (backend/app/schemas.py:95)
  - `{"title": "Status be28-$QA_TAG", "description": "Pole spoza modelu.", "category": "other", "status": "closed"}`: `422`, `detail[0].type` `extra_forbidden` (backend/app/schemas.py:88)
  - `{"title": "Zgłaszający be28-$QA_TAG", "description": "Pole spoza modelu.", "category": "other", "reporter_id": 1}`: `422`, `detail[0].type` `extra_forbidden` (backend/app/schemas.py:88)
  - POST `/api/tickets/{C}/comments` with `body` of 2001 × `x`: `422`, `detail[0].type` `string_too_long` (backend/app/schemas.py:126)
  - POST `/api/tickets/{C}/comments` `{"body": "ok", "author_id": 1}`: `422`, `detail[0].type` `extra_forbidden` (backend/app/schemas.py:124)

### BE-29: Ticket ids outside 1…2⁶³−1 are rejected with 422, never a server error
- **Area:** `TicketId = Annotated[int, Path(ge=1, le=MAX_SQLITE_INTEGER)]`
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie.
  2. Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account and retain owner's `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
- **Method:** GET /api/tickets/99999999999999999999
- **Headers:** `Cookie:` agent's `session` cookie
- **Payload:** none
- **Expected:** `422`; `detail[0].type` `less_than_equal` and `detail[0].loc` `["path", "ticket_id"]` (backend/app/routers/tickets.py:70) (backend/app/schemas.py:10)
- **Edge cases:**
  - PATCH `/api/tickets/99999999999999999999` `{"status": "closed"}` as agent: `422` (backend/app/routers/tickets.py:70)
  - POST `/api/tickets/99999999999999999999/comments` `{"body": "x"}` as agent: `422` (backend/app/routers/tickets.py:70)
  - `GET /api/tickets/0` as agent: `422`, `detail[0].type` `greater_than_equal` (backend/app/routers/tickets.py:70)
  - The main request as owner: `422` (backend/app/routers/tickets.py:156-158)
  - The main request without a cookie: `401` — the session dependency runs before path validation (backend/.venv/lib/python3.14/site-packages/fastapi/dependencies/utils.py:704) (backend/.venv/lib/python3.14/site-packages/fastapi/dependencies/utils.py:776-778)
  - PATCH `/api/tickets/99999999999999999999` `{"status": "closed"}` as owner: `403` — the role dependency runs first (backend/app/dependencies.py:56-67)

## Out of harness scope
- The session cookie's `Secure`, `SameSite=Strict`, `Max-Age=28800` and `Path=/` attributes and its deletion attributes on logout (backend/app/routers/auth.py:132-140) (backend/app/routers/auth.py:152-158) — qa-redact masks the whole `Set-Cookie` value and page scripts cannot read cookie attributes; `HttpOnly` is checked by FE-02 and the stored 480-minute lifetime by BE-12.
- Session expiry after 30 idle minutes or 8 hours, the `idle_timeout` and `absolute_timeout` rejections and the purge of expired rows at login (backend/app/sessions.py:26-32) (backend/app/sessions.py:67-76) — reaching either limit needs waiting out the window or rewriting `sessions` timestamps, and State Checks are read-only.
- The JSON events of the `patchpoint.security` log (`user_registered`, `registration_conflict`, `login_succeeded`, `login_failed`, `login_blocked`, `logout`, `session_rejected`, `access_denied`, `ticket_updated`, `demo_data_seeded`) and `internal_error` in `patchpoint.errors`, including the absence of passwords and tokens (backend/app/audit.py:23-33) — the API's log stream is not a browser, HTTP or database surface.
- The generic `500` body `{"detail": "Internal server error", "error_id": <32 hex characters>}` for database and unhandled errors (backend/app/main.py:18-38) — no HTTP input reaches such an error in the patched API, and producing one needs fault injection such as dropping a table.
- Settings that need a different API start: documentation served under `PATCHPOINT_DOCS_ENABLED=true`, a `*` in `PATCHPOINT_CORS_ORIGINS` refused, seeding without or with a weak `PATCHPOINT_DEMO_PASSWORD` refused, `PATCHPOINT_COOKIE_SECURE=false`, the refusal to start on a Phase 1 database (`schema version 0`) and idempotent seeding across restarts (backend/app/config.py:26-43) (backend/app/database.py:259-282) — restarting the API with other environment is service bring-up.
- Demo employees `jan.kowalski` and `anna.nowak` signing in with `PATCHPOINT_DEMO_PASSWORD` (backend/app/database.py:44-48) — the harness exposes that password only as the configured agent's credential; every agent scenario signs in with it.
- Rejection of a stored legacy MD5 hash (backend/app/security.py:21-25) — it needs a Phase 1 hash written into `users`, and State Checks are read-only.
- Equal response time for unknown usernames (backend/app/security.py:28-29) — timing is not a deterministic HTTP assertion; the identical status and body are checked by BE-13 and BE-14.
- The client's `Nie udało się wylogować: …` message (frontend/app.js:385-388) and its `Błąd serwera (HTTP <status>)` fallback (frontend/app.js:110) — both need the API to fail or be unreachable during a session, which the browser harness cannot induce.
- `make security-check` (22 `[NAPRAWIONE]`), `make demo`, `make lint`, `make typecheck` and `make test` with coverage ≥ 80% — repository scripts and build tooling, not browser, HTTP or database actions; the BE scenarios mirror the security script's API probes.
