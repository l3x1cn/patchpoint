# Test Plan: PatchPoint Phase 1 MVP — helpdesk API and static client

## Source
- Type: last 5 commits
- Base: main
- Range: `HEAD~5...HEAD` (`0885616`..`6d8f085`)
- Date: 2026-11-16
- Branch: delivery/faza-1-mvp
- Head: 6d8f085f5ea5da2d71cfa265633129dd3139e7bb

## Changes Summary

The last five commits on `delivery/faza-1-mvp` add the complete Phase 1 MVP of PatchPoint, a helpdesk for reporting IT hardware failures (36 new files). Every commit carries `Delivery-Plan: docs/plans/2026-11-15-faza-1-mvp.md`; that path passed validation (repository-relative, no `..`, no symlinked component, a regular file inside the repository), and its Task blocks and Verification section are this plan's specification. No trailer was rejected.

| Commit | Delivery-Task-Title | Delivery plan task |
|---|---|---|
| `bbeb8cd` | Backend — szkielet API, SQLite i uwierzytelnianie sesyjne | Task 1 |
| `5e89a0d` | Backend — zgłoszenia, przepływ statusów, komentarze i dane demo | Task 2 |
| `9013051` | Frontend — statyczny klient HTML/JS na osobnym originie | Task 3 |
| `8a968e9` | Skrypt demonstracyjny end-to-end | Task 4 |
| `6d8f085` | Dokumentacja Fazy 1, rejestr słabości i dowody działania | Task 5 |

Changed files by class:
- BE — FastAPI API served on the `backend` target (`backend/app/`): app factory with CORS and the database-error handler (`main.py`), settings (`config.py`), SQLite helpers and demo data (`database.py`, `schema.sql`), session-cookie lookup and the agent guard (`dependencies.py`), models and enums (`schemas.py`), password and session-token helpers (`security.py`), and the routers `health.py`, `auth.py` (register, login, logout, me) and `tickets.py` (create, role-scoped list with `status`/`search` filters, detail with comments, agent-only PATCH with the status workflow and assignment, comments).
- FE — static client served on the `ui` target (`frontend/index.html`, `frontend/app.js`, `frontend/styles.css`): sign-in and sign-up forms, ticket form, filter form, ticket table, detail panel with comments and agent-only actions, Polish labels. It calls the API with `credentials: "include"`, so the session travels in the `session` cookie.
- neither — `.gitignore`, `Makefile`, `README.md`, `backend/.python-version`, `backend/pyproject.toml`, `backend/uv.lock`, `backend/tests/**`, `docs/faza-1-dev/**` and `scripts/demo.sh` (demo tooling; its API flow is covered by BE scenarios). No DESKTOP code changed.

Intended contract (delivery plan Tasks 1–3):
- Auth: `POST /api/auth/register` → `201` user, role `employee` by default; `409` taken username; `422` invalid input. `POST /api/auth/login` → `200` plus the `session` cookie; `401` wrong password; `404` unknown username; `422`. `POST /api/auth/logout` → `200` `{"message": "Logged out"}` and the cookie deleted. `GET /api/auth/me` → `200` or `401` (`Not authenticated` / `Invalid session token`).
- Tickets, all `401` without a session: create → `201` (`open`, reporter = caller, priority `medium` by default), `422` for invalid enums or empty text; list → `200`, employees see only their own tickets and agents all of them, optional `status` (`422` when invalid) and ASCII case-insensitive `search` over title and description, newest first; detail → `200` with comments in creation order, `404`; PATCH is agent-only (`403`) and checks, in order, empty update `400`, unknown ticket `404`, a transition outside `open→{in_progress, closed}`, `in_progress→{open, resolved}`, `resolved→{in_progress, closed}` (`closed` is terminal, an unchanged status is allowed) `400`, an assignee that is not an agent `400`; comments → `201`, `404` unknown ticket, `422` empty body.
- `GET /api/health` → `200` `status: ok` without a session; a CORS preflight from the `ui` origin is answered with that origin and credentials allowed.
- Client: start-up session check through `/api/auth/me`, sign-in/sign-up, ticket form, filters, list, detail with comments, agent-only status and assignment actions.

The deliberate Phase 1 weaknesses W-01…W-18 are required behaviour that QA must not remove (docs/plans/2026-11-15-faza-1-mvp.md:20), listed in the register (docs/faza-1-dev/rejestr-slabosci.md:9-26). The scenarios therefore assert business behaviour and the Task 1–3 contracts only: they never probe a weakness and never expect its hardened replacement. They send no search-injection or apostrophe payloads (W-14, W-01), no HTML in ticket data (W-17), no foreign-origin CORS probes (W-13), no session reuse after logout and no bearer tokens (W-10, W-11), and they do not check `password_hash` (W-06), empty passwords (W-12), self-assigned roles (W-15) or an employee's access to another employee's ticket detail or comments (W-16). Where a specified error status coincides with a weakness (unknown-username `404`, W-05; `409` for a taken username, whose raw message is W-02), the scenario asserts the specified status, not the message wording. The `DatabaseError` → `500` JSON response (backend/app/main.py:34-46) is excluded on purpose as well: that handler is weakness W-01 itself (docs/faza-1-dev/rejestr-slabosci.md:9), and its only HTTP trigger is the W-14 search injection, which the delivery plan's own acceptance check exercises (docs/plans/2026-11-15-faza-1-mvp.md:828-830).

## Blockers / Findings

None found.

The hard-coded `debug=True` (backend/app/main.py:23), the wildcard credentialed CORS (backend/app/main.py:26-32) and the other W-01…W-18 items are specified Phase 1 requirements, not defects that obstruct testing.

## Users
- owner: registered — plain employee (signup default role `employee`) who files and follows tickets; username `qa+$QA_TAG-owner@test.local`, full name `QA Owner $QA_TAG`, department `QA`
- other: registered — second plain employee for list-scoping checks; username `qa+$QA_TAG-other@test.local`, full name `QA Other $QA_TAG`, department `QA`
- newcomer: registered — fresh employee account for the signup and login scenarios, files no tickets; username `qa+$QA_TAG-newcomer@test.local`, full name `QA Newcomer $QA_TAG`
- agent: existing — Helpdesk agent (role `agent`) for status changes, assignment and the all-tickets view. The signup form has no role field and API role self-assignment is weakness W-15, so configure an existing agent account such as the seeded demo agent `helpdesk` (README.md:81). PatchPoint logs in by username, so `qa.users.agent.email` holds that username.

Anonymous actions use no credential: FE-01, BE-01, BE-02 and the no-cookie edges.

## Detected Tools
- Playwright MCP: available (OMP built-in browser)
- HTTP client: curl (httpie unavailable); jq and perl JSON::PP available
- Store clients: sqlite3 available; psql, mysql and redis-cli unavailable. No store is configured and no scenario uses a State Check: every effect is observable through the API.
- Desktop drivers: none

## FE Test Scenarios

Every FE scenario runs in the browser on the `ui` target; the page itself calls the API (frontend/app.js:1). Start each scenario at `/`; if the user bar is visible, click "Wyloguj" first. Ticket titles carry `$QA_TAG`, so row assertions are unaffected by other data.

### FE-01: Anonymous visitor lands on the sign-in view
- **Area:** start-up session check and auth view (`init`, `#auth-view`)
- **Target:** ui
- **Writes:** no
- **Preconditions:** A browser context without a `session` cookie for `localhost` (nobody logged in).
- **Steps:**
  1. Open `/`
  2. Wait for the "Logowanie" heading
- **Expected:** The "Logowanie" form (Login, Hasło, "Zaloguj") and the "Rejestracja" form (Login, Imię i nazwisko, Dział, Hasło, "Zarejestruj konto") are visible; the app view ("Nowe zgłoszenie", "Zgłoszenia") and the user bar with "Wyloguj" are hidden; `#message` is empty, because the start-up `/api/auth/me` 401 only switches to the auth view (frontend/app.js:344-360)
- **Edge cases:**
  - The "Rejestracja" form has exactly the inputs Login, Imię i nazwisko, Dział and Hasło — no role field (frontend/index.html:40-55)
  - The page title is "PatchPoint — Helpdesk IT" and the header shows "PatchPoint" with the subtitle "System zgłoszeń awarii sprzętu IT" (frontend/index.html:6) (frontend/index.html:14-15)

### FE-02: Sign up through the Rejestracja form
- **Area:** registration form `#register-form`
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is shown, click "Wyloguj".
- **Steps:**
  1. In "Rejestracja" fill Login `qa+$QA_TAG-newcomer@test.local`, Imię i nazwisko `QA Newcomer $QA_TAG`, Dział `QA` and Hasło `$QA_NEW_PASSWORD`
  2. Click "Zarejestruj konto"; record the newcomer account immediately (the UI shows no id)
- **Expected:** `#message` shows "Konto utworzone — możesz się zalogować" in the success style; every "Rejestracja" field is cleared; the auth view stays visible and the user bar stays hidden, because signing up does not log in (frontend/app.js:296-297)
- **Edge cases:**
  - Fill "Rejestracja" again with the same Login `qa+$QA_TAG-newcomer@test.local`, Imię i nazwisko `QA Newcomer $QA_TAG` and Hasło `$QA_NEW_PASSWORD`, then submit: `#message` shows an error in the error style instead of the success text, and the form keeps the typed values (frontend/app.js:298-299)
  - Leave Imię i nazwisko empty (Login `qa+$QA_TAG-noname@test.local`) and click "Zarejestruj konto": the browser's required-field check blocks the submit and `#message` does not change (frontend/index.html:46)
  - Login `ab` with Imię i nazwisko `QA Short $QA_TAG` and Hasło `$QA_NEW_PASSWORD`, then click "Zarejestruj konto": no account is created and "Konto utworzone — możesz się zalogować" does not appear — the browser enforces the 3-character minimum (frontend/index.html:43), and a value that bypasses it is rejected by the API minimum (backend/app/schemas.py:13)

### FE-03: Log in, keep the session across reloads, log out
- **Area:** `#login-form`, user bar, session restore
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is shown, click "Wyloguj". Unless this dispatch already registered newcomer, register it through "Rejestracja" (Login `qa+$QA_TAG-newcomer@test.local`, Imię i nazwisko `QA Newcomer $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account.
- **Steps:**
  1. In "Logowanie" fill Login `qa+$QA_TAG-newcomer@test.local` and Hasło `$QA_NEW_PASSWORD`
  2. Click "Zaloguj"
- **Expected:** The auth view hides; the app view shows "Nowe zgłoszenie" and "Zgłoszenia"; `#user-info` reads "Zalogowano: QA Newcomer $QA_TAG (pracownik)"; the ticket table holds the single row "Brak zgłoszeń." because newcomer has filed nothing (frontend/app.js:100) (frontend/app.js:105-107)
- **Edge cases:**
  - Reload the page while logged in: the app view and "Zalogowano: QA Newcomer $QA_TAG (pracownik)" come back without logging in again, restored from the `session` cookie (frontend/app.js:344-353)
  - Click "Wyloguj", then reload: the auth view is shown both times and the user bar stays hidden, because logout deletes the `session` cookie (frontend/app.js:303-310) (backend/app/routers/auth.py:63-66)
  - Logged out, submit "Logowanie" with Login `qa+$QA_TAG-newcomer@test.local` and Hasło `wrong-password`: `#message` shows an error in the error style and the app view stays hidden (frontend/app.js:278-279)
  - Reload `/`, so the page starts logged out with an empty `#message`, then submit "Logowanie" with Login `qa+$QA_TAG-nobody@test.local` and Hasło `wrong-password`: `#message` shows an error in the error style and the app view stays hidden (backend/app/routers/auth.py:47-48)

### FE-04: File a ticket through "Nowe zgłoszenie"
- **Area:** ticket form `#ticket-form` and table `#ticket-list`
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is shown, click "Wyloguj". Unless this dispatch already registered owner, register it through "Rejestracja" (Login `qa+$QA_TAG-owner@test.local`, Imię i nazwisko `QA Owner $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account. Log in through "Logowanie" with Login `qa+$QA_TAG-owner@test.local` and Hasło `$QA_NEW_PASSWORD`. In "Zgłoszenia" choose Status "Wszystkie", clear Szukaj and click "Filtruj".
- **Steps:**
  1. In "Nowe zgłoszenie" fill Tytuł `Stacja dokująca FE04 $QA_TAG`, choose Kategoria "Urządzenie peryferyjne" and Priorytet "Wysoki", fill Nr inwentarzowy `DOC-$QA_TAG`, Lokalizacja `Pokój B12` and Opis `Po podłączeniu laptopa oba monitory pozostają czarne.`
  2. Click "Wyślij zgłoszenie"
- **Expected:** `#message` shows "Zgłoszenie wysłane"; the form resets (Tytuł, Nr inwentarzowy, Lokalizacja and Opis empty, Kategoria back to "Laptop", Priorytet back to "Średni"); the top row of the table shows Tytuł `Stacja dokująca FE04 $QA_TAG`, Kategoria "Urządzenie peryferyjne", Priorytet "Wysoki", Status "Otwarte", Zgłaszający "QA Owner $QA_TAG", Przypisany "—" and a pl-PL date under Utworzono (frontend/app.js:327-329) (frontend/app.js:113-121)
- **Edge cases:**
  - Leave Tytuł empty (Opis filled) and click "Wyślij zgłoszenie": the required-field check blocks the submit before the submit handler runs, so `#message` keeps its previous text and the table keeps the same rows (frontend/index.html:64)
  - Fill Tytuł `Pusty opis FE04 $QA_TAG`, clear Opis and click "Wyślij zgłoszenie": blocked the same way — `#message` keeps its previous text and no `Pusty opis FE04 $QA_TAG` row appears (frontend/index.html:93)
  - Submit only Tytuł `Mysz FE04 $QA_TAG` and Opis `Kursor się nie porusza.`, every other field at its default: the new row shows Kategoria "Laptop" and Priorytet "Średni", and its detail shows "Nr inwentarzowy: —" and "Lokalizacja: —" because empty fields are sent as null (frontend/app.js:323-324)

### FE-05: Employee opens a ticket and adds a comment
- **Area:** detail panel `#ticket-detail` and `#comment-form`
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is shown, click "Wyloguj". Unless this dispatch already registered owner, register it through "Rejestracja" (Login `qa+$QA_TAG-owner@test.local`, Imię i nazwisko `QA Owner $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account. Log in through "Logowanie" with Login `qa+$QA_TAG-owner@test.local` and Hasło `$QA_NEW_PASSWORD`; choose Status "Wszystkie" with an empty Szukaj and click "Filtruj". Through "Nowe zgłoszenie" file Tytuł `Drukarka FE05 $QA_TAG`, Kategoria "Drukarka", Priorytet "Niski", Nr inwentarzowy `PRN-$QA_TAG`, Lokalizacja `Korytarz`, Opis `Drukarka zacina papier przy druku dwustronnym.`
- **Steps:**
  1. Click the `Drukarka FE05 $QA_TAG` row
  2. In "Nowy komentarz" type `Proszę o pilną naprawę FE05 $QA_TAG`
  3. Click "Dodaj komentarz"
- **Expected:** After step 1 the panel shows the heading "#<id> Drukarka FE05 $QA_TAG", the "Otwarte" badge, "Kategoria: Drukarka", "Priorytet: Niski", "Nr inwentarzowy: PRN-$QA_TAG", "Lokalizacja: Korytarz", "Zgłaszający: QA Owner $QA_TAG", "Przypisany: —", the description and "Brak komentarzy." under "Komentarze"; after step 3 `#message` shows "Komentarz dodany" and the comment list shows "QA Owner $QA_TAG", a date and `Proszę o pilną naprawę FE05 $QA_TAG` (frontend/app.js:183-201) (frontend/app.js:235-236)
- **Edge cases:**
  - The employee's panel has no status select, no "Zmień status" and no "Przypisz do mnie" (frontend/app.js:150-153)
  - Click "Dodaj komentarz" with an empty "Nowy komentarz": the required-field check blocks the submit before the comment handler runs, so `#message` keeps its previous text and the comment list gains no entry (frontend/app.js:204)
  - Add a second comment `Drugi komentarz FE05 $QA_TAG`: both comments are listed, the first above the second (backend/app/routers/tickets.py:101)

### State combinations — filter form (FE-06…FE-09)

`currentFilterQuery()` adds each filter field only when it is non-empty (frontend/app.js:133-143): a Status other than "Wszystkie" and a non-empty Szukaj are independent inputs. The caller's role changes only which tickets the API returns (backend/app/routers/tickets.py:81-82); the client code has no role branch for listing, so the role axis is covered by the BE matrix (BE-07…BE-14) and these scenarios run as owner (employee).

| # | Status ≠ "Wszystkie" | Szukaj non-empty | Classification | Scenario |
|---|---|---|---|---|
| 1 | no | no | real | FE-06 |
| 2 | yes | no | real | FE-07 |
| 3 | no | yes | real | FE-08 |
| 4 | yes | yes | real | FE-09 |

### FE-06: Filter with Status "Wszystkie" and an empty Szukaj
- **Area:** `#filter-form` → ticket list without query parameters
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is shown, click "Wyloguj". Unless this dispatch already registered owner, register it through "Rejestracja" (Login `qa+$QA_TAG-owner@test.local`, Imię i nazwisko `QA Owner $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account. Log in through "Logowanie" with Login `qa+$QA_TAG-owner@test.local` and Hasło `$QA_NEW_PASSWORD`. Through "Nowe zgłoszenie" file `Toner FE06 $QA_TAG` (Kategoria "Drukarka", Opis `Kaseta z tonerem jest pusta.`) and then `Klawiatura FE06 $QA_TAG` (Kategoria "Urządzenie peryferyjne", Opis `Klawisze się zacinają.`).
- **Steps:**
  1. In "Zgłoszenia" choose Status "Wszystkie" and clear Szukaj
  2. Click "Filtruj"
- **Expected:** Both `Klawiatura FE06 $QA_TAG` and `Toner FE06 $QA_TAG` are listed, the newer `Klawiatura FE06 $QA_TAG` above the older one, and every row's Zgłaszający is "QA Owner $QA_TAG" (backend/app/routers/tickets.py:81-89)
- **Edge cases:**
  - Reload the page: the list loads by itself, without a "Filtruj" click, and shows both FE06 tickets again (frontend/app.js:351-353)
  - Click "Wyloguj"; unless this dispatch already registered other, register it through "Rejestracja" (Login `qa+$QA_TAG-other@test.local`, Imię i nazwisko `QA Other $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account; log in through "Logowanie" with Login `qa+$QA_TAG-other@test.local` and Hasło `$QA_NEW_PASSWORD`, choose Status "Wszystkie" with an empty Szukaj and click "Filtruj": neither FE06 ticket is listed (backend/app/routers/tickets.py:81-82)

### FE-07: Filter by Status only
- **Area:** `#filter-form` → `status` query parameter
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is shown, click "Wyloguj". Unless this dispatch already registered owner, register it through "Rejestracja" (Login `qa+$QA_TAG-owner@test.local`, Imię i nazwisko `QA Owner $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account. Log in through "Logowanie" with Login `qa+$QA_TAG-owner@test.local` and Hasło `$QA_NEW_PASSWORD`. Through "Nowe zgłoszenie" file `Drukarka FE07 $QA_TAG` (Opis `Zacina papier.`) and `Skaner FE07 $QA_TAG` (Opis `Nie skanuje.`); both start as "Otwarte".
- **Steps:**
  1. Choose Status "Otwarte" and clear Szukaj
  2. Click "Filtruj"
- **Expected:** Both FE07 tickets are listed and every listed row's Status badge reads "Otwarte" (backend/app/routers/tickets.py:83-84)
- **Edge cases:**
  - Status "W realizacji", empty Szukaj, "Filtruj": neither FE07 ticket is listed; every row shown has the "W realizacji" badge, or the table shows "Brak zgłoszeń." (backend/app/routers/tickets.py:83-84)
  - Status "Zamknięte", empty Szukaj, "Filtruj": neither FE07 ticket is listed; every row shown has the "Zamknięte" badge, or the table shows "Brak zgłoszeń." (backend/app/routers/tickets.py:83-84) (frontend/app.js:105-107)

### FE-08: Filter by Szukaj only
- **Area:** `#filter-form` → `search` query parameter
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is shown, click "Wyloguj". Unless this dispatch already registered owner, register it through "Rejestracja" (Login `qa+$QA_TAG-owner@test.local`, Imię i nazwisko `QA Owner $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account. Log in through "Logowanie" with Login `qa+$QA_TAG-owner@test.local` and Hasło `$QA_NEW_PASSWORD`. Through "Nowe zgłoszenie" file `Toner FE08 $QA_TAG` (Opis `Kaseta pusta.`) and `Klawiatura FE08 $QA_TAG` (Opis `Klawisze się zacinają, kod opis-fe08-$QA_TAG.`).
- **Steps:**
  1. Choose Status "Wszystkie" and fill Szukaj `toner fe08 $QA_TAG`
  2. Click "Filtruj"
- **Expected:** Exactly one row, `Toner FE08 $QA_TAG` — the title matches regardless of ASCII letter case (backend/app/routers/tickets.py:85-86)
- **Edge cases:**
  - Szukaj `opis-fe08-$QA_TAG`: exactly one row, `Klawiatura FE08 $QA_TAG` (the match is in the description) (backend/app/routers/tickets.py:86)
  - Szukaj `brak-fe08-$QA_TAG`: the table shows "Brak zgłoszeń." (frontend/app.js:105-107)

### FE-09: Filter by Status and Szukaj together
- **Area:** `#filter-form` → `status` and `search` query parameters
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is shown, click "Wyloguj". Unless this dispatch already registered owner, register it through "Rejestracja" (Login `qa+$QA_TAG-owner@test.local`, Imię i nazwisko `QA Owner $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account. Log in through "Logowanie" with Login `qa+$QA_TAG-owner@test.local` and Hasło `$QA_NEW_PASSWORD`. Through "Nowe zgłoszenie" file `Toner FE09 $QA_TAG` (Opis `Kaseta pusta.`) and `Klawiatura FE09 $QA_TAG` (Opis `Klawisze się zacinają.`); both start as "Otwarte".
- **Steps:**
  1. Choose Status "Otwarte" and fill Szukaj `toner fe09 $QA_TAG`
  2. Click "Filtruj"
- **Expected:** Exactly one row, `Toner FE09 $QA_TAG` with the "Otwarte" badge (backend/app/routers/tickets.py:83-88)
- **Edge cases:**
  - Status "Zamknięte" with the same Szukaj: the table shows "Brak zgłoszeń.", because both conditions must hold (backend/app/routers/tickets.py:88)
  - Status "Otwarte" with Szukaj `klawiatura fe09 $QA_TAG`: exactly one row, `Klawiatura FE09 $QA_TAG` (backend/app/routers/tickets.py:83-88)

### FE-10: Helpdesk agent takes over, works and closes a ticket
- **Area:** agent actions in `#ticket-detail` (status select, "Zmień status", "Przypisz do mnie")
- **Target:** ui
- **Writes:** yes
- **Preconditions:** Open `/`; if the user bar is shown, click "Wyloguj". Unless this dispatch already registered owner, register it through "Rejestracja" (Login `qa+$QA_TAG-owner@test.local`, Imię i nazwisko `QA Owner $QA_TAG`, Dział `QA`, Hasło `$QA_NEW_PASSWORD`) and record the account. Log in through "Logowanie" with Login `qa+$QA_TAG-owner@test.local` and Hasło `$QA_NEW_PASSWORD`, file `Monitor FE10 $QA_TAG` (Kategoria "Monitor", Opis `Monitor miga po podłączeniu przez HDMI.`) through "Nowe zgłoszenie" and click "Wyloguj". Log in through "Logowanie" with Login `$QA_AGENT_EMAIL` and Hasło `$QA_AGENT_PASSWORD`, and note the full name shown in `#user-info`.
- **Steps:**
  1. Choose Status "Wszystkie", fill Szukaj `Monitor FE10 $QA_TAG` and click "Filtruj"
  2. Click the `Monitor FE10 $QA_TAG` row
  3. Click "Przypisz do mnie"
  4. Choose "W realizacji" in the status select and click "Zmień status"
  5. In "Nowy komentarz" type `Sprawdzam kabel HDMI FE10 $QA_TAG` and click "Dodaj komentarz"
  6. Choose "Rozwiązane" and click "Zmień status"
  7. Choose "Zamknięte" and click "Zmień status"
- **Expected:** `#user-info` ends with "(agent Helpdesk)"; the row shows Zgłaszający "QA Owner $QA_TAG"; the panel offers the status select (pre-set to "Otwarte"), "Zmień status" and "Przypisz do mnie"; step 3 shows "Zgłoszenie przypisane do Ciebie" and "Przypisany: <the agent's full name>"; step 4 shows "Status zmieniony" and the "W realizacji" badge; step 5 shows "Komentarz dodany" with the agent's name on the comment; steps 6 and 7 move the badge to "Rozwiązane" and then "Zamknięte"; the table row ends with Status "Zamknięte" and Przypisany set to the agent's full name (frontend/app.js:154-165) (frontend/app.js:245-260)
- **Edge cases:**
  - In the same panel, now "Zamknięte", choose "Otwarte" and click "Zmień status": `#message` shows an error containing "Invalid status transition" (closed -> open) (exact text — brittle) and the badge stays "Zamknięte" (backend/app/routers/tickets.py:125-128)
  - As agent, file `Zasilacz FE10 $QA_TAG` (Opis `Nie ładuje.`) through "Nowe zgłoszenie", fill Szukaj `Zasilacz FE10 $QA_TAG`, click "Filtruj", open it, choose "Rozwiązane" and click "Zmień status": an error containing "Invalid status transition" (open -> resolved) (exact text — brittle) appears and the badge stays "Otwarte" (backend/app/routers/tickets.py:21)
  - Click "Wyloguj", log in through "Logowanie" with Login `qa+$QA_TAG-owner@test.local` and Hasło `$QA_NEW_PASSWORD`, choose Status "Wszystkie", fill Szukaj `Monitor FE10 $QA_TAG`, click "Filtruj" and open the ticket: the "Zamknięte" badge, "Przypisany: <the agent's full name>" and the agent's comment are shown, and the owner's panel has no agent actions (frontend/app.js:150-153)

## BE Test Scenarios

Sessions travel in the `session` cookie, as the client uses them: retain it from each login's `Set-Cookie` and send it as `Cookie`. A scenario registers owner, other or newcomer only if this dispatch has not done so yet. Letters such as A, B, T name the `id` values retained from the scenario's own ticket-creation requests.

### BE-01: Health endpoint answers without a session
- **Area:** `GET /api/health`
- **Target:** backend
- **Writes:** no
- **Preconditions:** none; anonymous request without a cookie
- **Method:** GET /api/health
- **Headers:** none
- **Payload:** none
- **Expected:** `200`, JSON body with `status` equal to `"ok"` (backend/app/routers/health.py:17-18)
- **Edge cases:**
  - Same request with `Cookie: session=forged`: still `200` with `status` `"ok"` — the endpoint has no session dependency (backend/app/routers/health.py:13-14)
  - Same request with `Origin: http://localhost:5500`: `200` plus `access-control-allow-origin: http://localhost:5500` and `access-control-allow-credentials: true` (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:159-164)

### BE-02: CORS preflight admits the UI origin with credentials
- **Area:** CORS middleware — the contract the static client on `http://localhost:5500` relies on
- **Target:** backend
- **Writes:** no
- **Preconditions:** none; anonymous request without a cookie
- **Method:** OPTIONS /api/auth/me
- **Headers:** `Origin: http://localhost:5500`, `Access-Control-Request-Method: GET`
- **Payload:** none
- **Expected:** `200`; `access-control-allow-origin` is exactly `http://localhost:5500` and `access-control-allow-credentials` is `true` (backend/app/main.py:26-32) (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:111-115)
- **Edge cases:**
  - Add `Access-Control-Request-Headers: content-type`, which every client call needs because it sends `Content-Type: application/json` (frontend/app.js:52): `200` and `access-control-allow-headers` echoes `content-type` (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:124-125)
  - Plain `GET /api/auth/me` with `Origin: http://localhost:5500` and no cookie: `401` that still carries `access-control-allow-origin: http://localhost:5500` and `access-control-allow-credentials: true`, so the client can read the 401 at start-up (backend/.venv/lib/python3.14/site-packages/starlette/middleware/cors.py:159-164)

### BE-03: Register a new account, employee by default
- **Area:** `POST /api/auth/register`
- **Target:** backend
- **Writes:** yes
- **Preconditions:** none. The main request registers newcomer: record the account and retain newcomer's `id` immediately after the `201`.
- **Method:** POST /api/auth/register
- **Headers:** `Content-Type: application/json`
- **Payload:** `{"username": "qa+$QA_TAG-newcomer@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Newcomer $QA_TAG", "department": "QA"}`
- **Expected:** `201`; body with `username` `qa+$QA_TAG-newcomer@test.local`, `full_name` `QA Newcomer $QA_TAG`, `department` `QA`, `role` `employee` (the signup default) and the keys `id` and `created_at` (backend/app/routers/auth.py:37-41) (backend/app/schemas.py:17)
- **Edge cases:**
  - A second registration with the same `username` `qa+$QA_TAG-newcomer@test.local` (`full_name` `QA Newcomer Duplicate $QA_TAG`, same password): `409` with a string `detail` beginning `Registration failed` (exact text — brittle) (backend/app/routers/auth.py:30-34)
  - Payload without `username`: `422` (backend/app/schemas.py:13)
  - `username` `ab`: `422`, below the 3-character minimum (backend/app/schemas.py:13)
  - `username` of 51 characters — `qa+$QA_TAG-`, then 28 × `x`, then `@test.local`: `422`, above the 50-character maximum (backend/app/schemas.py:13)
  - `full_name` `""` with `username` `qa+$QA_TAG-noname@test.local`: `422` (backend/app/schemas.py:15)

### BE-04: Log in with username and password
- **Area:** `POST /api/auth/login`
- **Target:** backend
- **Writes:** yes
- **Preconditions:** Unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`); record the account and retain owner's `id`.
- **Method:** POST /api/auth/login
- **Headers:** `Content-Type: application/json`
- **Payload:** `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}`
- **Expected:** `200`; `user.username` `qa+$QA_TAG-owner@test.local`, `user.full_name` `QA Owner $QA_TAG`, `user.role` `employee`, `user.department` `QA`; the response has a `set-cookie` header (its value is masked by qa-redact) — retain the `session` cookie (backend/app/routers/auth.py:52-60)
- **Edge cases:**
  - Password `wrong-password`: `401` and no `set-cookie` header (backend/app/routers/auth.py:49-50)
  - Username `qa+$QA_TAG-nobody@test.local`, never registered: `404` (Phase 1 contract) and no `set-cookie` header (backend/app/routers/auth.py:47-48)
  - Payload without `password`: `422` (backend/app/schemas.py:30-32)

### BE-05: Current user from the session cookie, and logout
- **Area:** `GET /api/auth/me`, `POST /api/auth/logout`
- **Target:** backend
- **Writes:** yes
- **Preconditions:** Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account, retain `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
- **Method:** GET /api/auth/me
- **Headers:** `Cookie:` owner's `session` cookie retained in Preconditions (tester-owned, not a plan token)
- **Payload:** none
- **Expected:** `200`; `username` `qa+$QA_TAG-owner@test.local`, `full_name` `QA Owner $QA_TAG`, `role` `employee`, `department` `QA` (backend/app/dependencies.py:42-50)
- **Edge cases:**
  - No cookie: `401` with `detail` `Not authenticated` (exact text — brittle) (backend/app/dependencies.py:39-40)
  - `Cookie: session=forged`: `401` with `detail` `Invalid session token` (exact text — brittle) (backend/app/dependencies.py:47-48)
  - POST `/api/auth/logout` with owner's cookie: `200` `{"message": "Logged out"}` and a `set-cookie` header (value masked; the browser-side deletion is checked by FE-03) (backend/app/routers/auth.py:63-66)

### BE-06: Create a ticket
- **Area:** `POST /api/tickets`
- **Target:** backend
- **Writes:** yes
- **Preconditions:** Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account, retain `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
- **Method:** POST /api/tickets
- **Headers:** `Content-Type: application/json`; `Cookie:` owner's `session` cookie
- **Payload:** `{"title": "Stacja dokująca BE06 $QA_TAG", "description": "Po podłączeniu laptopa oba monitory pozostają czarne.", "category": "peripheral", "priority": "high", "asset_tag": "DOC-$QA_TAG", "location": "Pokój B12"}`
- **Expected:** `201`; `status` `open`, `category` `peripheral`, `priority` `high`; `title`, `description`, `asset_tag` and `location` equal the payload; `reporter_name` `QA Owner $QA_TAG`; `assignee_id` and `assignee_name` `null`; `created_at` equals `updated_at` (backend/app/routers/tickets.py:47-70)
- **Edge cases:**
  - Same payload without a cookie: `401` (backend/app/dependencies.py:39-40)
  - Minimal payload `{"title": "Mysz BE06 $QA_TAG", "description": "Kursor się nie porusza.", "category": "laptop"}`: `201` with `priority` `medium`, `asset_tag` `null` and `location` `null` (backend/app/schemas.py:80-82)
  - `"category": "toaster"` in the main payload: `422` (backend/app/schemas.py:52-59)
  - `"priority": "urgent"` in the main payload: `422` (backend/app/schemas.py:62-66)
  - `"title": ""` in the main payload: `422` (backend/app/schemas.py:77)
  - `"description": ""` in the main payload: `422` (backend/app/schemas.py:78)

### State combinations — ticket list (BE-07…BE-14)

`GET /api/tickets` builds its filter from three independent inputs (backend/app/routers/tickets.py:81-86): the caller's role (an `employee` adds `t.reporter_id = <own id>`, an `agent` adds nothing), a `status` query value and a non-empty `search` value. The conditions are joined with `AND`, and the title-or-description search pair is parenthesised (backend/app/routers/tickets.py:86-88), so a search must never widen an employee's scope. Unauthenticated callers never reach this code (backend/app/dependencies.py:39-40); they are covered by edges.

| # | Role is employee | `status` set | `search` set | Classification | Scenario |
|---|---|---|---|---|---|
| 1 | yes | no | no | real | BE-07 |
| 2 | yes | yes | no | real | BE-08 |
| 3 | yes | no | yes | real | BE-09 |
| 4 | yes | yes | yes | real | BE-10 |
| 5 | no (agent) | no | no | real | BE-11 |
| 6 | no (agent) | yes | no | real | BE-12 |
| 7 | no (agent) | no | yes | real | BE-13 |
| 8 | no (agent) | yes | yes | real | BE-14 |

### BE-07: Employee list without filters shows only own tickets
- **Area:** `GET /api/tickets` — matrix row 1
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account, retain `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
  2. Other session — unless this dispatch already registered other: POST `/api/auth/register` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Other $QA_TAG", "department": "QA"}` (`201`), record the account, retain `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
  3. As owner, POST `/api/tickets` `{"title": "Laptop a07 $QA_TAG", "description": "Ekran gaśnie po starcie.", "category": "laptop"}` (`201`).
  4. As other, POST `/api/tickets` `{"title": "Monitor b07 $QA_TAG", "description": "Monitor miga.", "category": "monitor"}` (`201`).
- **Method:** GET /api/tickets
- **Headers:** `Cookie:` owner's `session` cookie
- **Payload:** none
- **Expected:** `200`; the array contains `Laptop a07 $QA_TAG` and not `Monitor b07 $QA_TAG`; every element's `reporter_name` is `QA Owner $QA_TAG`, and elements are in descending `id` order (backend/app/routers/tickets.py:81-82) (backend/app/routers/tickets.py:89)
- **Edge cases:**
  - Same request with other's cookie: `200`; contains `Monitor b07 $QA_TAG` and not `Laptop a07 $QA_TAG`; every `reporter_name` is `QA Other $QA_TAG` (backend/app/routers/tickets.py:81-82)
  - No cookie: `401` (backend/app/dependencies.py:39-40)

### BE-08: Employee list filtered by status
- **Area:** `GET /api/tickets?status=` — matrix row 2
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner and other sessions — register each user only if this dispatch has not registered it yet, then always log in:
     - Owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`; record the account, retain `id`); POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`); retain the `session` cookie.
     - Other: POST `/api/auth/register` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Other $QA_TAG", "department": "QA"}` (`201`; record the account, retain `id`); POST `/api/auth/login` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`); retain the `session` cookie.
  2. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie.
  3. As owner, POST `/api/tickets` `{"title": "Drukarka a08 $QA_TAG", "description": "Zacina papier.", "category": "printer"}` (A) and `{"title": "Skaner c08 $QA_TAG", "description": "Nie skanuje.", "category": "peripheral"}` (C).
  4. As other, POST `/api/tickets` `{"title": "Monitor b08 $QA_TAG", "description": "Miga.", "category": "monitor"}` (B).
  5. As agent, PATCH `/api/tickets/{A}` and `/api/tickets/{B}` with `{"status": "in_progress"}` (`200` each); C stays `open`.
- **Method:** GET /api/tickets?status=in_progress
- **Headers:** `Cookie:` owner's `session` cookie
- **Payload:** none
- **Expected:** `200`; contains `Drukarka a08 $QA_TAG`; excludes `Monitor b08 $QA_TAG` (another employee's — role scope) and `Skaner c08 $QA_TAG` (still open — status filter); every element has `status` `in_progress` and `reporter_name` `QA Owner $QA_TAG` (backend/app/routers/tickets.py:81-84)
- **Edge cases:**
  - `GET /api/tickets?status=open` as owner: `200`; contains `Skaner c08 $QA_TAG`, excludes `Drukarka a08 $QA_TAG` and `Monitor b08 $QA_TAG`; every element is `open` (backend/app/routers/tickets.py:83-84)
  - `GET /api/tickets?status=pending` as owner: `422` (backend/app/routers/tickets.py:77)

### BE-09: Employee list filtered by search
- **Area:** `GET /api/tickets?search=` — matrix row 3
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner and other sessions — register each user only if this dispatch has not registered it yet, then always log in:
     - Owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`; record the account, retain `id`); POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`); retain the `session` cookie.
     - Other: POST `/api/auth/register` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Other $QA_TAG", "department": "QA"}` (`201`; record the account, retain `id`); POST `/api/auth/login` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`); retain the `session` cookie.
  2. As owner, POST `/api/tickets` in this order: `{"title": "Toner be09-$QA_TAG", "description": "Kaseta pusta.", "category": "printer"}`, `{"title": "Klawiatura c09 $QA_TAG", "description": "Klawisze się zacinają.", "category": "peripheral"}`, `{"title": "Drukarka d09 $QA_TAG", "description": "Brak tonera, kod be09-$QA_TAG.", "category": "printer"}`.
  3. As other, POST `/api/tickets` `{"title": "Monitor b09 $QA_TAG", "description": "Kod be09-$QA_TAG w opisie.", "category": "monitor"}`.
- **Method:** GET /api/tickets?search=be09-$QA_TAG
- **Headers:** `Cookie:` owner's `session` cookie
- **Payload:** none
- **Expected:** `200`; exactly two elements, `Drukarka d09 $QA_TAG` (description match) then `Toner be09-$QA_TAG` (title match); `Klawiatura c09 $QA_TAG` (no match) and `Monitor b09 $QA_TAG` (another employee's ticket that matches in its description) are absent (backend/app/routers/tickets.py:81-86)
- **Edge cases:**
  - `search=BE09-$QA_TAG`: the same two elements — ASCII letter case is ignored (backend/app/routers/tickets.py:86)
  - `search=` with an empty value: treated as no search — contains `Toner be09-$QA_TAG`, `Klawiatura c09 $QA_TAG` and `Drukarka d09 $QA_TAG`, not `Monitor b09 $QA_TAG` (backend/app/routers/tickets.py:85)
  - `search=nomatch-$QA_TAG`: `200` with `[]` (backend/app/routers/tickets.py:86)

### BE-10: Employee list filtered by status and search
- **Area:** `GET /api/tickets?status=&search=` — matrix row 4
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner and other sessions — register each user only if this dispatch has not registered it yet, then always log in:
     - Owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`; record the account, retain `id`); POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`); retain the `session` cookie.
     - Other: POST `/api/auth/register` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Other $QA_TAG", "department": "QA"}` (`201`; record the account, retain `id`); POST `/api/auth/login` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`); retain the `session` cookie.
  2. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie.
  3. As owner, POST `/api/tickets` `{"title": "Drukarka be10-$QA_TAG", "description": "Zacina papier.", "category": "printer"}` (A), `{"title": "Skaner be10-$QA_TAG", "description": "Nie skanuje.", "category": "peripheral"}` (C) and `{"title": "Klawiatura e10 $QA_TAG", "description": "Nie działa.", "category": "peripheral"}` (E).
  4. As other, POST `/api/tickets` `{"title": "Monitor be10-$QA_TAG", "description": "Miga.", "category": "monitor"}` (B).
  5. As agent, PATCH A, B and E with `{"status": "in_progress"}` (`200` each); C stays `open`.
- **Method:** GET /api/tickets?status=in_progress&search=be10-$QA_TAG
- **Headers:** `Cookie:` owner's `session` cookie
- **Payload:** none
- **Expected:** `200`; exactly one element, `Drukarka be10-$QA_TAG`: `Skaner be10-$QA_TAG` fails the status filter, `Klawiatura e10 $QA_TAG` fails the search and `Monitor be10-$QA_TAG` is outside the role scope (backend/app/routers/tickets.py:80-89)
- **Edge cases:**
  - `status=open&search=be10-$QA_TAG` as owner: exactly `Skaner be10-$QA_TAG` (backend/app/routers/tickets.py:83-88)
  - `status=closed&search=be10-$QA_TAG` as owner: `200` with `[]` (backend/app/routers/tickets.py:88)

### BE-11: Agent list without filters shows every reporter's tickets
- **Area:** `GET /api/tickets` — matrix row 5
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner and other sessions — register each user only if this dispatch has not registered it yet, then always log in:
     - Owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`; record the account, retain `id`); POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`); retain the `session` cookie.
     - Other: POST `/api/auth/register` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Other $QA_TAG", "department": "QA"}` (`201`; record the account, retain `id`); POST `/api/auth/login` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`); retain the `session` cookie.
  2. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie.
  3. As owner, POST `/api/tickets` `{"title": "Laptop a11 $QA_TAG", "description": "Nie uruchamia się.", "category": "laptop"}` (A); then as other `{"title": "Monitor b11 $QA_TAG", "description": "Miga.", "category": "monitor"}` (B).
- **Method:** GET /api/tickets
- **Headers:** `Cookie:` agent's `session` cookie
- **Payload:** none
- **Expected:** `200`; contains `Laptop a11 $QA_TAG` with `reporter_name` `QA Owner $QA_TAG` and `Monitor b11 $QA_TAG` with `reporter_name` `QA Other $QA_TAG`, B listed before A, and the whole array is in descending `id` order — an agent gets no reporter condition (backend/app/routers/tickets.py:81-82) (backend/app/routers/tickets.py:88-89)
- **Edge cases:**
  - `Cookie: session=forged`: `401` with `detail` `Invalid session token` (exact text — brittle) (backend/app/dependencies.py:47-48)
  - Every element carries the keys `id`, `title`, `description`, `category`, `priority`, `status`, `asset_tag`, `location`, `reporter_id`, `reporter_name`, `assignee_id`, `assignee_name`, `created_at` and `updated_at` (backend/app/schemas.py:91-105)

### BE-12: Agent list filtered by status
- **Area:** `GET /api/tickets?status=` — matrix row 6
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner and other sessions — register each user only if this dispatch has not registered it yet, then always log in:
     - Owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`; record the account, retain `id`); POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`); retain the `session` cookie.
     - Other: POST `/api/auth/register` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Other $QA_TAG", "department": "QA"}` (`201`; record the account, retain `id`); POST `/api/auth/login` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`); retain the `session` cookie.
  2. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie.
  3. As owner, POST `/api/tickets` `{"title": "Laptop a12 $QA_TAG", "description": "Nie uruchamia się.", "category": "laptop"}` (A); as other `{"title": "Monitor b12 $QA_TAG", "description": "Miga.", "category": "monitor"}` (B).
  4. As agent, PATCH `/api/tickets/{B}` with `{"status": "in_progress"}` (`200`).
- **Method:** GET /api/tickets?status=in_progress
- **Headers:** `Cookie:` agent's `session` cookie
- **Payload:** none
- **Expected:** `200`; contains `Monitor b12 $QA_TAG` (no role scope for an agent) and not `Laptop a12 $QA_TAG` (open); every element has `status` `in_progress` (backend/app/routers/tickets.py:81-84)
- **Edge cases:**
  - `status=open` as agent: contains `Laptop a12 $QA_TAG`, not `Monitor b12 $QA_TAG`; every element is `open` (backend/app/routers/tickets.py:83-84)
  - `status=IN_PROGRESS` as agent: `422`, the values are lower-case (backend/app/schemas.py:69-73)

### BE-13: Agent list filtered by search
- **Area:** `GET /api/tickets?search=` — matrix row 7
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner and other sessions — register each user only if this dispatch has not registered it yet, then always log in:
     - Owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`; record the account, retain `id`); POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`); retain the `session` cookie.
     - Other: POST `/api/auth/register` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Other $QA_TAG", "department": "QA"}` (`201`; record the account, retain `id`); POST `/api/auth/login` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`); retain the `session` cookie.
  2. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie.
  3. In this order: as owner POST `/api/tickets` `{"title": "Toner be13-$QA_TAG", "description": "Kaseta pusta.", "category": "printer"}`; as other `{"title": "Monitor b13 $QA_TAG", "description": "Kod be13-$QA_TAG w opisie.", "category": "monitor"}`; as owner `{"title": "Klawiatura c13 $QA_TAG", "description": "Nie działa.", "category": "peripheral"}`.
- **Method:** GET /api/tickets?search=be13-$QA_TAG
- **Headers:** `Cookie:` agent's `session` cookie
- **Payload:** none
- **Expected:** `200`; exactly two elements, `Monitor b13 $QA_TAG` (other's, description match) then `Toner be13-$QA_TAG` (owner's, title match); `Klawiatura c13 $QA_TAG` is absent (backend/app/routers/tickets.py:85-89)
- **Edge cases:**
  - `search=BE13-$QA_TAG`: the same two elements (backend/app/routers/tickets.py:86)
  - `search=nomatch-$QA_TAG`: `200` with `[]` (backend/app/routers/tickets.py:86)

### BE-14: Agent list filtered by status and search
- **Area:** `GET /api/tickets?status=&search=` — matrix row 8
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner and other sessions — register each user only if this dispatch has not registered it yet, then always log in:
     - Owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`; record the account, retain `id`); POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`); retain the `session` cookie.
     - Other: POST `/api/auth/register` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Other $QA_TAG", "department": "QA"}` (`201`; record the account, retain `id`); POST `/api/auth/login` `{"username": "qa+$QA_TAG-other@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`); retain the `session` cookie.
  2. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie.
  3. As owner POST `/api/tickets` `{"title": "Drukarka be14-$QA_TAG", "description": "Zacina papier.", "category": "printer"}` (A); as other `{"title": "Monitor be14-$QA_TAG", "description": "Miga.", "category": "monitor"}` (B); as owner `{"title": "Klawiatura c14 $QA_TAG", "description": "Nie działa.", "category": "peripheral"}` (C).
  4. As agent, PATCH A and C with `{"status": "in_progress"}` (`200` each); B stays `open`.
- **Method:** GET /api/tickets?status=in_progress&search=be14-$QA_TAG
- **Headers:** `Cookie:` agent's `session` cookie
- **Payload:** none
- **Expected:** `200`; exactly one element, `Drukarka be14-$QA_TAG`: `Monitor be14-$QA_TAG` fails the status filter and `Klawiatura c14 $QA_TAG` fails the search (backend/app/routers/tickets.py:83-89)
- **Edge cases:**
  - `status=open&search=be14-$QA_TAG` as agent: exactly `Monitor be14-$QA_TAG` (backend/app/routers/tickets.py:83-88)
  - `status=resolved&search=be14-$QA_TAG` as agent: `200` with `[]` (backend/app/routers/tickets.py:88)

### BE-15: Ticket detail with an empty comment list
- **Area:** `GET /api/tickets/{ticket_id}`
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account, retain `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
  2. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie.
  3. As owner, POST `/api/tickets` `{"title": "Monitor be15-$QA_TAG", "description": "Miga po podłączeniu przez HDMI.", "category": "monitor", "priority": "low", "asset_tag": "MON-$QA_TAG", "location": "C-012"}` (T).
- **Method:** GET /api/tickets/{T}
- **Headers:** `Cookie:` owner's `session` cookie
- **Payload:** none
- **Expected:** `200`; `title` `Monitor be15-$QA_TAG`, `status` `open`, `priority` `low`, `asset_tag` `MON-$QA_TAG`, `location` `C-012`, `reporter_name` `QA Owner $QA_TAG`, `assignee_name` `null` and `comments` an empty list (backend/app/routers/tickets.py:94-105)
- **Edge cases:**
  - Same request with the agent's cookie: `200` with the same `title` and `reporter_name` — agents read every ticket (backend/app/routers/tickets.py:94)
  - `GET /api/tickets/999999999` as owner: `404` (backend/app/routers/tickets.py:97-98)
  - `GET /api/tickets/abc` as owner: `422` (backend/app/routers/tickets.py:95)
  - No cookie: `401` (backend/app/routers/tickets.py:94)

### BE-16: Comment on a ticket
- **Area:** `POST /api/tickets/{ticket_id}/comments`
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account, retain `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
  2. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie and the response's `user.full_name`.
  3. As owner, POST `/api/tickets` `{"title": "Drukarka be16-$QA_TAG", "description": "Zacina papier.", "category": "printer"}` (T).
- **Method:** POST /api/tickets/{T}/comments
- **Headers:** `Content-Type: application/json`; `Cookie:` owner's `session` cookie
- **Payload:** `{"body": "Proszę o pilną naprawę be16-$QA_TAG"}`
- **Expected:** `201`; `ticket_id` equals T, `author_name` is `QA Owner $QA_TAG`, `body` equals the payload and `created_at` is present (backend/app/routers/tickets.py:166-178)
- **Edge cases:**
  - Then `GET /api/tickets/{T}` as owner: `comments` holds that comment with `author_name` `QA Owner $QA_TAG`, and the ticket's `updated_at` equals the comment's `created_at` (backend/app/routers/tickets.py:166-172)
  - As agent, POST `/api/tickets/{T}/comments` `{"body": "Sprawdzam be16-$QA_TAG"}`: `201` with `author_name` equal to the agent's `user.full_name`; a following `GET /api/tickets/{T}` lists owner's comment first and the agent's second (backend/app/routers/tickets.py:101)
  - `{"body": ""}` as owner: `422` (backend/app/schemas.py:108-109)
  - POST `/api/tickets/999999999/comments` `{"body": "x"}` as owner: `404` (backend/app/routers/tickets.py:162-164)
  - The main request without a cookie: `401` (backend/app/dependencies.py:39-40)

### State combinations — PATCH fields (BE-17…BE-19)

`PATCH /api/tickets/{ticket_id}` takes three optional fields, `status`, `priority` and `assignee_id` (backend/app/schemas.py:85-88). Behind the agent guard (BE-20), the handler rejects a body with none of them, then checks that the ticket exists, that a present `status` is an allowed transition and that a present `assignee_id` is an agent, in that order (backend/app/routers/tickets.py:112-133), and writes every present field in one `UPDATE` (backend/app/routers/tickets.py:135-149). No rule ties the fields to each other, so every presence combination is real. The `200` checks of rows 2, 3 and 6–8 run on BE-19's fresh `open` tickets T3…T7.

| # | `status` | `priority` | `assignee_id` | Classification | Scenario |
|---|---|---|---|---|---|
| 1 | no | no | no | real | BE-19 edges 3 and 5 (`400`, checked before the ticket lookup) |
| 2 | no | no | yes | real | BE-19 edge 9 (agent assignee, `200`); edges 1–2 (non-agent or unknown assignee, `400`) |
| 3 | no | yes | no | real | BE-19 edge 10 (`200`); edge 4 (unknown ticket, `404`); edge 8 (invalid `priority` value, `422`) |
| 4 | no | yes | yes | real | BE-19 main (`200`) |
| 5 | yes | no | no | real | BE-17 and BE-18 (every cell of the transition table below) |
| 6 | yes | no | yes | real | BE-19 edge 11 (`200`; the take-over request `make demo` sends, scripts/demo.sh:80-81); edges 6–7 (`400`, the transition is checked before the assignee) |
| 7 | yes | yes | no | real | BE-19 edge 12 (`200`) |
| 8 | yes | yes | yes | real | BE-19 edge 13 (`200`) |

### Status transitions — ALLOWED_TRANSITIONS coverage (BE-17, BE-18)

Rows are the current status and columns the requested one (backend/app/routers/tickets.py:20-25); an unchanged status is accepted as a no-op (backend/app/routers/tickets.py:122). Every cell has a check:

| from \ to | open | in_progress | resolved | closed |
|---|---|---|---|---|
| open | 200 no-op — BE-18 edge 2 | 200 — BE-17 main | 400 — BE-18 edge 1 | 200 — BE-18 main |
| in_progress | 200 — BE-18 edge 3 | 200 no-op — BE-18 edge 5 | 200 — BE-17 edge 1 | 400 — BE-18 edge 4 |
| resolved | 400 — BE-18 edge 7 | 200 — BE-18 edge 6 | 200 no-op — BE-18 edge 8 | 200 — BE-17 edge 2 |
| closed | 400 — BE-17 edge 3 | 400 — BE-17 edge 4 | 400 — BE-17 edge 5 | 200 no-op — BE-17 edge 6 |

### BE-17: Agent moves a ticket forward to closed; closed is terminal
- **Area:** `PATCH /api/tickets/{ticket_id}` — status workflow
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account, retain `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
  2. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie.
  3. As owner, POST `/api/tickets` `{"title": "Laptop be17-$QA_TAG", "description": "Nie uruchamia się po aktualizacji.", "category": "laptop"}` (T). The main request and then the edges run in order on T, all as agent.
- **Method:** PATCH /api/tickets/{T}
- **Headers:** `Content-Type: application/json`; `Cookie:` agent's `session` cookie
- **Payload:** `{"status": "in_progress"}`
- **Expected:** `200`; `status` `in_progress`, with `title` and `reporter_name` unchanged (backend/app/routers/tickets.py:21) (backend/app/routers/tickets.py:135-155)
- **Edge cases:**
  - Then `{"status": "resolved"}`: `200`, `status` `resolved` (backend/app/routers/tickets.py:22)
  - Then `{"status": "closed"}`: `200`, `status` `closed` (backend/app/routers/tickets.py:23)
  - Then `{"status": "open"}`: `400` with `detail` `Invalid status transition: closed -> open` (exact text — brittle) (backend/app/routers/tickets.py:24)
  - Then `{"status": "in_progress"}`: `400` with `detail` `Invalid status transition: closed -> in_progress` (exact text — brittle) (backend/app/routers/tickets.py:125-128)
  - Then `{"status": "resolved"}`: `400` with `detail` `Invalid status transition: closed -> resolved` (exact text — brittle) (backend/app/routers/tickets.py:125-128)
  - Then `{"status": "closed"}`: `200`, an unchanged status is a no-op, and `GET /api/tickets/{T}` still shows `closed` (backend/app/routers/tickets.py:122)

### BE-18: Direct close, return to the queue, reopen and the forbidden skips
- **Area:** `PATCH /api/tickets/{ticket_id}` — status workflow
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account, retain `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie.
  2. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie.
  3. As owner, POST `/api/tickets` four times with `{"title": "Zgłoszenie <n> be18-$QA_TAG", "description": "Przepływ statusów.", "category": "other"}` for n = 1, 2, 3, 4 (T1…T4, all `open`). Every PATCH below is sent as agent, and each edge works only on the ticket it names.
- **Method:** PATCH /api/tickets/{T1}
- **Headers:** `Content-Type: application/json`; `Cookie:` agent's `session` cookie
- **Payload:** `{"status": "closed"}`
- **Expected:** `200`; `status` `closed` — an open ticket may be closed directly, for example as a duplicate (backend/app/routers/tickets.py:21)
- **Edge cases:**
  - T2 (open) `{"status": "resolved"}`: `400` with `detail` `Invalid status transition: open -> resolved` (exact text — brittle) (backend/app/routers/tickets.py:21)
  - T2 (open) `{"status": "open"}`: `200`, `status` `open` (no-op) (backend/app/routers/tickets.py:122)
  - T2: `{"status": "in_progress"}` (`200`), then `{"status": "open"}`: `200`, `status` `open` — back to the queue (backend/app/routers/tickets.py:22)
  - T3: `{"status": "in_progress"}` (`200`), then `{"status": "closed"}`: `400` with `detail` `Invalid status transition: in_progress -> closed` (exact text — brittle) (backend/app/routers/tickets.py:22)
  - T3 (in_progress) `{"status": "in_progress"}`: `200` (no-op) (backend/app/routers/tickets.py:122)
  - T3: `{"status": "resolved"}` (`200`), then `{"status": "in_progress"}`: `200`, `status` `in_progress` — reopened (backend/app/routers/tickets.py:23)
  - T4: `{"status": "in_progress"}` (`200`), `{"status": "resolved"}` (`200`), then `{"status": "open"}`: `400` with `detail` `Invalid status transition: resolved -> open` (exact text — brittle) (backend/app/routers/tickets.py:23)
  - T4 (resolved) `{"status": "resolved"}`: `200` (no-op) (backend/app/routers/tickets.py:122)

### BE-19: Agent assigns a helpdesk agent and changes priority
- **Area:** `PATCH /api/tickets/{ticket_id}` — assignment, priority, field combinations and validation order
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account, retain `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie. Owner's `id` below is the value retained at owner's registration in this dispatch.
  2. Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie, `user.id` and `user.full_name`.
  3. As owner, POST `/api/tickets` `{"title": "Monitor be19-$QA_TAG", "description": "Brak obrazu.", "category": "monitor"}` (T) and `{"title": "Mysz be19-$QA_TAG", "description": "Kursor skacze.", "category": "peripheral"}` (T2), then five times `{"title": "Zgłoszenie <n> be19-$QA_TAG", "description": "Kombinacja pól.", "category": "other"}` for n = 3, 4, 5, 6, 7 (T3…T7). Each ticket starts `open` with `priority` `medium` and no assignee; each edge works only on the ticket it names. Every PATCH below is sent as agent.
- **Method:** PATCH /api/tickets/{T}
- **Headers:** `Content-Type: application/json`; `Cookie:` agent's `session` cookie
- **Payload:** `{"assignee_id": <agent's user.id>, "priority": "critical"}`
- **Expected:** `200`; `assignee_name` equals the agent's `user.full_name`, `assignee_id` is not null, `priority` is `critical` and `status` is still `open` (backend/app/routers/tickets.py:130-155)
- **Edge cases:**
  - T `{"assignee_id": <owner's id>}`: `400` with `detail` `Assignee must be a helpdesk agent` (exact text — brittle) (backend/app/routers/tickets.py:130-133)
  - T `{"assignee_id": 999999999}`: `400` with the same `detail` (exact text — brittle) (backend/app/routers/tickets.py:131-133)
  - T `{}`: `400` with `detail` `Nothing to update` (exact text — brittle) (backend/app/routers/tickets.py:112-113)
  - `PATCH /api/tickets/999999999` `{"priority": "low"}`: `404` (backend/app/routers/tickets.py:115-117)
  - `PATCH /api/tickets/999999999` `{}`: `400` with `detail` `Nothing to update` — the empty-update check runs before the lookup (exact text — brittle) (backend/app/routers/tickets.py:112-117)
  - T2 (open) `{"status": "resolved", "assignee_id": <owner's id>}`: `400` with `detail` `Invalid status transition: open -> resolved` — the transition check runs before the assignee check (exact text — brittle) (backend/app/routers/tickets.py:119-133)
  - T2 (open) `{"status": "in_progress", "assignee_id": <owner's id>}`: `400` with `detail` `Assignee must be a helpdesk agent`, and `GET /api/tickets/{T2}` still shows `status` `open` and `assignee_id` `null` — nothing is written when validation fails (exact text — brittle) (backend/app/routers/tickets.py:130-149)
  - T `{"priority": "urgent"}`: `422` (backend/app/schemas.py:62-66)
  - T3 (open) `{"assignee_id": <agent's user.id>}`: `200`; `assignee_name` equals the agent's `user.full_name`, `status` stays `open` and `priority` stays `medium` (backend/app/routers/tickets.py:135-149)
  - T4 (open) `{"priority": "low"}`: `200`; `priority` `low`, `status` stays `open` and `assignee_name` stays `null` (backend/app/routers/tickets.py:135-149)
  - T5 (open) `{"status": "in_progress", "assignee_id": <agent's user.id>}`: `200`; `status` `in_progress` and `assignee_name` equals the agent's `user.full_name`, while `priority` stays `medium` (backend/app/routers/tickets.py:135-149)
  - T6 (open) `{"status": "in_progress", "priority": "high"}`: `200`; `status` `in_progress` and `priority` `high`, while `assignee_name` stays `null` (backend/app/routers/tickets.py:135-149)
  - T7 (open) `{"status": "in_progress", "priority": "critical", "assignee_id": <agent's user.id>}`: `200`; `status` `in_progress`, `priority` `critical` and `assignee_name` equal to the agent's `user.full_name` (backend/app/routers/tickets.py:135-149)

### BE-20: Only agents may change a ticket
- **Area:** `PATCH /api/tickets/{ticket_id}` — agent role guard
- **Target:** backend
- **Writes:** yes
- **Preconditions:**
  1. Owner session — unless this dispatch already registered owner: POST `/api/auth/register` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD", "full_name": "QA Owner $QA_TAG", "department": "QA"}` (`201`), record the account, retain `id`. Then POST `/api/auth/login` `{"username": "qa+$QA_TAG-owner@test.local", "password": "$QA_NEW_PASSWORD"}` (`200`) and retain the `session` cookie. Owner's `id` below is the value retained at owner's registration in this dispatch.
  2. As owner, POST `/api/tickets` `{"title": "Skaner be20-$QA_TAG", "description": "Nie skanuje.", "category": "peripheral"}` (T).
- **Method:** PATCH /api/tickets/{T}
- **Headers:** `Content-Type: application/json`; `Cookie:` owner's `session` cookie
- **Payload:** `{"status": "closed"}`
- **Expected:** `403`, and `GET /api/tickets/{T}` as owner still shows `status` `open` (backend/app/dependencies.py:56-58)
- **Edge cases:**
  - The main request without a cookie: `401` (backend/app/dependencies.py:39-40)
  - As owner, `PATCH /api/tickets/999999999` `{"status": "closed"}`: `403` — the role check runs before the ticket lookup (backend/app/routers/tickets.py:108)
  - As owner, PATCH T `{"assignee_id": <owner's id>}`: `403` (backend/app/dependencies.py:57-58)

### BE-21: Demo tickets and comment created by the API on an empty database
- **Area:** demo data `seed_demo_data`, read through `GET /api/tickets`
- **Target:** backend
- **Writes:** yes
- **Preconditions:** Agent session — POST `/api/auth/login` `{"username": "$QA_AGENT_EMAIL", "password": "$QA_AGENT_PASSWORD"}` (`200`); retain the `session` cookie. The API adds the demo data itself when it starts on an empty database with `PATCHPOINT_SEED_DEMO_DATA` at its default `true` (backend/app/database.py:130-133) (backend/app/config.py:14); if none of the three titles below exists, report NEED_INFO kind=fixture (database not initialised with demo data) instead of FAIL.
- **Method:** GET /api/tickets
- **Headers:** `Cookie:` agent's `session` cookie
- **Payload:** none
- **Expected:** `200`; contains `Laptop nie uruchamia się po aktualizacji` (`reporter_name` `Jan Kowalski`, `category` `laptop`, `priority` `high`, `status` `open`, `asset_tag` `LAP-0042`), `Drukarka zacina papier` (`reporter_name` `Jan Kowalski`, `category` `printer`, `priority` `medium`, `status` `in_progress`, `assignee_name` `Piotr Serwisant`, `asset_tag` `PRN-0007`, `location` `Korytarz, 2. piętro`) and `Migający monitor` (`reporter_name` `Anna Nowak`, `category` `monitor`, `priority` `low`, `status` `open`, `asset_tag` `MON-0113`, `location` `C-012`) (backend/app/database.py:145-180)
- **Edge cases:**
  - `GET /api/tickets/{id of Drukarka zacina papier}`: `200` with exactly one comment, `author_name` `Piotr Serwisant`, `body` `Zamówiono nowy podajnik papieru, wymiana planowana na piątek.` (backend/app/database.py:182-194)
  - `GET /api/tickets?search=HDMI` as agent: contains `Migający monitor`, matched in its description (backend/app/database.py:172)

## Out of harness scope
- `make demo` (`scripts/demo.sh`): its exit code and final line `DEMO ZAKOŃCZONE POWODZENIEM` — running a repository script is not a browser, HTTP or DB action. Its API flow is covered by BE-01, BE-04–BE-07, BE-09, BE-11, BE-15–BE-17 and BE-19, whose edge 11 sends the step-7 take-over request with `status` `in_progress` and the agent as `assignee_id` (scripts/demo.sh:80-81); the cookie removal on logout is covered by FE-03.
- Demo data written only into an empty `users` table, and only once across API restarts (backend/app/database.py:130-133) — this needs restarting the API on a fresh database, which is service bring-up; the resulting data is checked by BE-21.
- `make lint`, `make typecheck` and `make test` with coverage ≥ 80% — build tooling, not a browser, HTTP or DB action.
