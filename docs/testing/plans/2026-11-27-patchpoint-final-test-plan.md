# Test Plan: PatchPoint final tests — whole application and the instructor's review

## Setup

This section describes the environment of the run. Commands and code blocks are carried over verbatim; `$SFX`, `$RUN`, `$EVD`, `H`, `S`, `BASE`, `new_user`, `req`, `wave` and `summary` used by the scenarios below are defined here.

**At the start of every executing task**, in the repository root:

```bash
EVD=docs/testing/evidence/2026-11-27-patchpoint-final
mkdir -p "$EVD"
RUN=$(mktemp -d /tmp/pp-final.XXXXXX)   # 0700: hasła, ciasteczka, ciała żądań, kopie bazy
umask 077
SFX=$(python3 -c 'import secrets; print(secrets.token_hex(3))')
DEMO_PW=$(python3 -c 'import secrets; print("Final-" + secrets.token_urlsafe(18))')
printf '%s\n' "$DEMO_PW" > "$RUN/secrets.txt"
printf '%s' "$DEMO_PW" | jq -Rsc '{username: "helpdesk", password: .}' > "$RUN/login.helpdesk.json"

new_user() { # new_user LOGIN — $RUN/pw.LOGIN, $RUN/reg.LOGIN.json, $RUN/login.LOGIN.json
  local u="$1" pw
  pw=$(python3 -c 'import secrets; print("Qa-" + secrets.token_urlsafe(18))')
  printf '%s\n' "$pw" >> "$RUN/secrets.txt"
  printf '%s' "$pw" > "$RUN/pw.$u"
  printf '%s' "$pw" | jq -Rsc --arg u "$u" '{username: $u, password: ., full_name: "QA Final", department: "QA"}' > "$RUN/reg.$u.json"
  printf '%s' "$pw" | jq -Rsc --arg u "$u" '{username: $u, password: .}' > "$RUN/login.$u.json"
}
req() { # req METHOD PATH [curl args…] — prints "status seconds"; body in $RUN/last.body
  local m="$1" p="$2"; shift 2
  curl -s --noproxy '*' -m 60 -X "$m" -H 'Content-Type: application/json' -o "$RUN/last.body" -w '%{http_code} %{time_total}\n' "$@" "$BASE$p"
}
# wave NAME — runs every job of $RUN/NAME.jobs at once against $BASE, writes $RUN/NAME.out
# jobs: TSV id, method, path, body-file|-, cookie-in|-, cookie-out|-
# out:  TSV id, status, seconds, detail, retry-after
wave() {
  local name="$1" id method path body jin jout
  : > "$RUN/$name.out"
  while IFS=$'\t' read -r id method path body jin jout; do
    (
      args=(-s --noproxy '*' -m 120 -X "$method" -H 'Content-Type: application/json'
            -o "$RUN/$name.$id.body" -D "$RUN/$name.$id.hdr" -w '%{http_code}\t%{time_total}')
      [[ "$body" == - ]] || args+=(--data-binary "@$body")
      [[ "$jin" == - ]] || args+=(-b "$jin")
      [[ "$jout" == - ]] || args+=(-c "$jout")
      res=$(curl "${args[@]}" "$BASE$path") || res=$'000\t0'
      detail=$(jq -r 'if type == "object" and (.detail | type) == "string" then .detail else "" end' "$RUN/$name.$id.body" 2>/dev/null)
      retry=$(tr -d '\r' < "$RUN/$name.$id.hdr" 2>/dev/null | awk -F': ' 'tolower($1) == "retry-after" {print $2}')
      printf '%s\t%s\t%s\t%s\n' "$id" "$res" "$detail" "$retry" >> "$RUN/$name.out"
    ) &
  done < "$RUN/$name.jobs"
  wait
}
summary() { # summary NAME — status counts, detail counts, p50/p95/max seconds
  cut -f2 "$RUN/$1.out" | sort | uniq -c
  cut -f4 "$RUN/$1.out" | sort | uniq -c
  cut -f3 "$RUN/$1.out" | sort -n | awk '{a[NR]=$1} END {print "p50=" a[int(NR*0.5+0.5)] " p95=" a[int(NR*0.95+0.5)] " max=" a[NR]}'
}
```

**Development API instances** started with `make run`. Each is a single uvicorn process with `--no-proxy-headers` (Makefile:22), without a proxy, reachable at `http://127.0.0.1:<port>`.

| Name | Port | Database | Extra variables |
|---|---|---|---|
| dev | 18100 | `$RUN/dev/patchpoint.db` | `PATCHPOINT_SEED_DEMO_DATA=true`, `PATCHPOINT_DEMO_PASSWORD="$DEMO_PW"` |
| workers | 18101 | `$RUN/workers/patchpoint.db` | `WEB_CONCURRENCY=4` |
| docs | 18102 | `$RUN/docs/patchpoint.db` | `PATCHPOINT_DOCS_ENABLED=true` |

Start (example for `dev`). The variables are assigned as a shell prefix, so the password does not reach the process arguments. `$!` is the PGID, because `setsid` in the script does not fork.

```bash
mkdir -p "$RUN/dev"
PATCHPOINT_DATABASE_PATH="$RUN/dev/patchpoint.db" PATCHPOINT_SEED_DEMO_DATA=true PATCHPOINT_DEMO_PASSWORD="$DEMO_PW" \
  setsid make run API_PORT=18100 > "$RUN/dev/api.log" 2>&1 &
echo $! > "$RUN/dev/pgid"
for i in $(seq 60); do curl -sf --noproxy '*' -o /dev/null http://127.0.0.1:18100/api/health && break; sleep 1; done
```

Stop: `kill -TERM -- "-$(cat "$RUN/dev/pgid")"`. Database state check: `sqlite3 -readonly "$RUN/dev/patchpoint.db" "<SQL>"`.

**The `patchpoint-final` stack** runs in local mode: no redirect to HTTPS, HSTS 0 and the cookie named `session`. The `patchpoint-*:local` images come from OPS-01. When `docker image inspect patchpoint-api:local` fails, build them as in OPS-01.

```bash
export COMPOSE_PROJECT_NAME=patchpoint-final PATCHPOINT_API_IMAGE=patchpoint-api:local PATCHPOINT_PROXY_IMAGE=patchpoint-proxy:local
export PATCHPOINT_HTTP_BIND=127.0.0.1:28080 PATCHPOINT_HTTPS_BIND=127.0.0.1:28443 PATCHPOINT_HTTPS_PUBLIC_PORT=28443
export PATCHPOINT_PUBLIC_ORIGINS='["http://patchpoint.localhost:28080","https://patchpoint.localhost:28443"]'
export PATCHPOINT_BACKEND_SUBNET=10.253.0.0/24 PATCHPOINT_PROXY_BACKEND_IP=10.253.0.10
export PATCHPOINT_API_ENV_FILE="$RUN/stack-api.env"
printf 'PATCHPOINT_SEED_DEMO_DATA=true\nPATCHPOINT_DEMO_PASSWORD=%s\n' "$DEMO_PW" > "$RUN/stack-api.env"
make dev-cert && docker compose up -d --wait --wait-timeout 180
H=http://patchpoint.localhost:28080 ; S=https://patchpoint.localhost:28443   # HTTPS: curl --cacert deploy/proxy/dev-tls/fullchain.pem
```

Cleanup: `docker compose down -v` with the same variables.

**Request pacing through the proxy.** `/api/auth/login` and `/api/auth/register` share the rate-limit zone `patchpoint_auth`: 10 per minute, burst 5 (`deploy/proxy/templates/conf.d/patchpoint-limits.conf.template:3`, `deploy/proxy/Dockerfile:48-49`, `deploy/proxy/templates/includes/patchpoint-app.conf.template:28-36`).

- Before every authentication request through the proxy: `sleep 7`.
- Exceptions to this rule: FE-06, step 15 of OPS-04 and edge a) of OPS-05.
- After a scenario with a burst of requests, wait 65 s.

**Secrets and evidence.**

- **Where secrets are kept.** Passwords are kept only in files under `$RUN`. They reach curl through `--data-binary @file` and jq through stdin, never as a command argument. Tokens are kept only in curl cookie jars under `$RUN`.
- **Evidence content.** Evidence never contains request bodies, cookie values or `Set-Cookie` headers.
- **Block format.** Every block in an evidence file starts with a `$ <command>` line and states the exit code. Long output may be shortened with a `… [N lines omitted]` marker, but the lines that decide the result stay.
- **Scan before finishing a task.** First `awk '$6 ~ /session$/ {print $7}' "$RUN"/*.jar >> "$RUN/secrets.txt" 2>/dev/null || true`, then `grep -rnF -f "$RUN/secrets.txt" "$EVD"` — it must return nothing. Finally `rm -rf "$RUN"`.
- **Task results file** (`results-*.md`, in English) holds a table `| ID | Kind | Verdict | Evidence | Notes |`. Under the table every `Fail` or `Confirmed` result gets an entry `**<ID>** — Expected: … — Actual: …` with the evidence file and excerpt.
- **Cleanup.** A task ends with no `patchpoint-final-*`, `patchpoint-smoke*`, `pp-ansible-target` or `pp-verify-*` containers, no `patchpoint-final_*` or `pp-ansible-docker` volumes, and no process listening on ports 18100–18102. The user's containers stay untouched: the project `patchpoint`, `secure-k8s-aiops-*` and `vina-searxng`.

## Source
- Type: whole application on branch delivery/patchpoint-final-testing
- Base: 3444344 (root commit `init`)
- Date: 2026-11-27
- Branch: delivery/patchpoint-final-testing
- Head: 3d9b40a6c3e338f49eb11275e34a8477e3d89c36
- Provenance: written and executed by hand (curl, sqlite3, openssl, docker, gh, Chromium through the OMP `browser`); not generated by `/qa:create-plan` and not run by the `/qa:run` engine

## Changes Summary

Scope of the whole application: backend (FastAPI, SQLite), frontend (static UI), the reverse proxy with WAF (nginx, ModSecurity, OWASP CRS), the compose stack, the Ansible deployment roles and the CI workflow. The plan verifies the remarks of the instructor's review (sections 1, 2 and 3) and records the state of the application before any fix of this delivery.

The tests are run by hand, because ports 8080 and 8443 required by `/qa:run` are occupied.

Instructor's remarks and the scenarios that verify them (the identifiers are used in the scenario catalog and in the final report):

| ID | Review section | Uwaga (skrót) | Scenarios |
|---|---|---|---|
| R1.1 | 1 | Przejrzysty proces w trzech fazach, dokumentacja | none (process documentation) |
| R1.2 | 1 | Poprawki aplikacji: Argon2id, SHA-256 tokenów, SQL z ESCAPE, `extra="forbid"`, Origin i nagłówki, logi JSON, 22 PoC | OPS-01, OPS-04, FE-01–FE-05, BE-07 |
| R1.3 | 1 | Hardening kontenerów i sieci, WAF, limit żądań | OPS-01, OPS-02, OPS-03, OPS-06, OPS-08, FE-02, FE-06 |
| R1.4 | 1 | Potok CI/CD z bramkami i tym samym artefaktem | OPS-14, OPS-18 |
| R2.1 | 2 | Certyfikat tymczasowy roli Ansible bez CA:FALSE i SAN | OPS-16 |
| R2.2 | 2 | Kolejność handlerów w roli `base` | OPS-17 |
| R2.3 | 2 | `ExecStop` bez prefiksu `-` | OPS-17 |
| R2.4 | 2 | Brak dokumentacji QA Fazy 3 | OPS-15 |
| R2.5 | 2 | Wersja backendu 0.2.0 i opis „Faza 2” | BE-01 |
| R2.6 | 2 | Dowody CI sprzed późniejszych zmian | OPS-15, OPS-18 |
| R2.7 | 2 | Błąd składni Semgrepa, ShellCheck i actionlint poza CI | OPS-01, OPS-18 |
| R3.1 | 3 | SBOM i podpisywanie obrazów | OPS-14 |
| R3.2 | 3 | Determinizm reguł SAST | OPS-13 |
| R3.3 | 3 | Sekrety w historii gita i skany cykliczne | OPS-11, OPS-14 |
| R3.4 | 3 | Skanowanie IaC (compose, Ansible) | OPS-12 |
| R3.5 | 3 | Automatyczne podnoszenie proxy przy DoS | OPS-07 |
| R3.6 | 3 | Egress proxy | OPS-08 |
| R3.7 | 3 | Ochrona SSH i kopie zapasowe | OPS-09, OPS-10, OPS-16, OPS-17 |
| R3.8 | 3 | Współbieżność w SQLite | BE-02–BE-06, OPS-05 |
| R3.9 | 3 | Zarządzanie kontami i hasłami (IAM) | BE-07, BE-08 |
| R3.10 | 3 | Obserwowalność i SIEM | OPS-04 |

## Blockers / Findings

None found.

## Users
- owner: registered — qa.final.$SFX.owner (FE)
- agent: existing — seeded demo agent helpdesk, password = the run's PATCHPOINT_DEMO_PASSWORD
- employees: registered — qa.final.$SFX.<role> per scenario (BE, OPS)

## Detected Tools
- Browser: Chromium through the OMP `browser` (checked in Task 3)
- Command line: curl, jq, sqlite3, openssl, docker 29.10.0, docker compose 5.8.0, gh, uv 0.13.8
- Containers with pinned digests: gitleaks, KICS and curl
- Load generators: hey, wrk and ab are not available

## Verdict rules

- **Kind `contract`.** `Pass` when every Expected is met, including the edges. Otherwise `Fail`.
- **Kind `probe`.** Checks the instructor's claim of a missing capability (the "Remark claim"). The verdict is `Confirmed`, `Not confirmed` or `Partially confirmed`.
- **`Need info`.** When a tool or an environment is missing, record the named reason.
- **QA-NNN issues in the final report.** One is raised for every `Fail` and for every probe that incidentally reveals a defect: a 5xx, a crash or OOM, a lost security guarantee, or untrue documentation.
  - Severity per `qa:report-format`: status ≥ 500 or a crash → CRITICAL; a wrong status, wrong data or a lost guarantee → HIGH; a degradation → MEDIUM; documentation → LOW.
  - Missing capabilities from review section 3 go only to the remark matrix, without a QA-NNN.
- **Fix map.** Only the defects below are fixed. Each one in its own task and only when the named scenario has the verdict `Fail` in the baseline results. Every other `Fail` gets a QA-NNN with a proposed fix and no fix in this delivery.

| Defect | Trigger | Task |
|---|---|---|
| B1: API commit blocked by an external SQLite read | BE-05 `Fail` | Task 7 |
| B2: parallel Argon2 exceeds the API memory limit | OPS-05 `Fail` | Task 8 |
| B3: the number of uvicorn workers is not pinned | BE-06 `Fail` | Task 9 |
| B4: defects of the `base` and `docker` roles | failed OPS-17 checks caused by the role code | Task 10 |
| B5: documentation mismatches and no restore description | OPS-15 `Fail`; OPS-10 `Pass` | Task 11 |

## FE Test Scenarios

Chromium through the stack (`H` = `http://patchpoint.localhost:28080`). Driven through the OMP `browser` global in `eval` (read `xd://eval/browser` first). One tab: `browser.open(name="pp-final", url=H + "/")`. Use `tab.goto` and actions on visible labels or ids, and `tab.evaluate` for page state. Record the text of `#message` after every action. Wait `sleep 7` before every sign-up or sign-in submit, except in FE-06.

### FE-01: Sign-up and sign-in through the proxy
- **Kind:** contract
- **Remarks:** R1.2
- **Target:** ui (`H`)
- **Preconditions:** none
- **Steps:**
  1. In „Rejestracja” fill Login `qa.final.$SFX.owner`, „Imię i nazwisko” `QA Final Owner`, „Dział” `QA` and „Hasło” with the password from `new_user qa.final.$SFX.owner`, then click „Zarejestruj konto”.
  2. Run edges a) and b).
  3. In „Logowanie” fill the same login and password and click „Zaloguj”.
- **Expected:**
  - After step 1, `#message` reads „Konto utworzone — możesz się zalogować” (frontend/app.js:383).
  - After step 3, the app view is shown and the user bar reads „Zalogowano: QA Final Owner (pracownik)” (frontend/app.js:149).
  - `document.cookie` contains no `session=` (backend/app/routers/auth.py:149).
- **Edge cases:**
  - a) The same registration again → „Username is already taken” (backend/app/routers/auth.py:65).
  - b) Registration of `qa.final.$SFX.owner2` with password `qa.final.$SFX.owner2-Secret-12345` → the message contains „Password must not contain the username” (backend/app/security.py:45; exact text — brittle).

### FE-02: Employee ticket through the UI
- **Kind:** contract
- **Remarks:** R1.2, R1.3
- **Target:** ui (`H`)
- **Preconditions:** signed in as the FE-01 owner.
- **Steps:**
  1. In „Nowe zgłoszenie”: Tytuł `Drukarka nie drukuje $SFX`, Kategoria „Drukarka”, Priorytet „Wysoki”, Opis `Brak wydruku z kolejki.`; click „Wyślij zgłoszenie”.
  2. Click the row with that title.
  3. In „Nowy komentarz” type `Sprawdziłem kabel.` and click „Dodaj komentarz”.
- **Expected:**
  - After step 1: „Zgłoszenie wysłane” (frontend/app.js:418), and the list shows the title with badge „Otwarte” (frontend/app.js:23).
  - After step 2: the detail heading is `#<id> Drukarka nie drukuje $SFX`, and there is no `#status-select` or `#assign-button` (frontend/app.js:205).
  - After step 3: „Komentarz dodany” (frontend/app.js:308), and the comment text is shown.
- **Edge cases:**
  - a) Tytuł `<script>alert(1)</script>` with the other fields valid → „Request blocked by the proxy” (deploy/proxy/templates/includes/patchpoint-app.conf.template:41). No new row, no dialog, and the form keeps its values (frontend/app.js:417; the form is reset only on success).
  - b) „Szukaj” = `$SFX`, then „Filtruj” → exactly one row, the step-1 ticket (backend/app/routers/tickets.py:148).

### FE-03: Agent handles the ticket
- **Kind:** contract
- **Remarks:** R1.2
- **Target:** ui (`H`)
- **Preconditions:**
  1. The FE-02 ticket exists.
  2. Click „Wyloguj” → „Wylogowano” (frontend/app.js:399).
  3. Sign in as `helpdesk` with `$DEMO_PW`.
- **Steps:**
  1. Open the FE-02 ticket.
  2. Click „Przypisz do mnie”.
  3. In `#status-select` choose „W realizacji”, then click „Zmień status”.
  4. Do the same with „Rozwiązane”.
  5. Do the same with „Zamknięte”.
- **Expected:**
  - The user bar reads „Zalogowano: Piotr Serwisant (agent Helpdesk)” (backend/app/database.py:45; frontend/app.js:31).
  - Step 2 shows „Zgłoszenie przypisane do Ciebie” (frontend/app.js:332).
  - Steps 3–5 each show „Status zmieniony” (frontend/app.js:319), and the final badge is „Zamknięte” (frontend/app.js:26).
- **Edge cases:**
  - a) Choose „Otwarte” on the closed ticket and click „Zmień status” → „Invalid status transition: closed -> open” (backend/app/routers/tickets.py:197; transitions at backend/app/routers/tickets.py:25). The badge stays „Zamknięte”.
  - b) The agent's list has at least 4 rows, including the 3 seeded demo tickets (backend/app/routers/tickets.py:134; backend/app/database.py:50).

### FE-04: Session ended outside the UI
- **Kind:** contract
- **Remarks:** R1.2
- **Target:** ui (`H`)
- **Preconditions:** signed in as `helpdesk`.
- **Steps:**
  1. `tab.evaluate("fetch('/api/auth/logout', {method: 'POST', credentials: 'include'}).then(r => r.status)")` → 200.
  2. Click „Filtruj”.
- **Expected:** the auth view is shown with „Sesja wygasła lub została zakończona — zaloguj się ponownie.” (frontend/app.js:3 and the 401 branch at frontend/app.js:98-101).
- **Edge cases:**
  - a) Reload → the auth view is shown (frontend/app.js:438; the start-up call to `/api/auth/me` gets 401).
  - b) Sign in as `helpdesk` and click „Wyloguj” → „Wylogowano” (frontend/app.js:399). Then `fetch('/api/auth/me')` from the page → 401 (backend/app/dependencies.py:37).

### FE-05: CSP enforced by the proxy header
- **Kind:** contract
- **Remarks:** R1.2, R1.3
- **Target:** ui (`H`)
- **Preconditions:** `/` is loaded.
- **Steps**, in one `tab.evaluate`:
  1. Register a `securitypolicyviolation` listener that collects `violatedDirective`.
  2. Append a `<script>` element with text `window.__cspProbe = 1`.
  3. `try { eval('1') } catch (e) { evalError = e.name }`.
  4. `try { await fetch('https://example.com/') } catch (e) { fetchError = e.name }`.
  5. Wait 500 ms and return all values.
- **Expected** (deploy/proxy/templates/includes/patchpoint-app.conf.template:15; the `location /` header carries `script-src 'self'` and `connect-src 'self'`):
  - `window.__cspProbe` is undefined (deploy/proxy/templates/includes/patchpoint-app.conf.template:15).
  - At least one violated directive starts with `script-src` (deploy/proxy/templates/includes/patchpoint-app.conf.template:15).
  - `evalError` is `EvalError` (deploy/proxy/templates/includes/patchpoint-app.conf.template:15; no `unsafe-eval` in `script-src`).
  - `fetchError` is `TypeError` (deploy/proxy/templates/includes/patchpoint-app.conf.template:15).
- **Edge cases:**
  - a) The `meta[http-equiv="Content-Security-Policy"]` content contains `connect-src 'self'` (deploy/proxy/Dockerfile:16-17).
  - b) `fetch('/', {method: 'HEAD'})` headers: `x-frame-options` = `DENY`, and `content-security-policy` contains `frame-ancestors 'none'` (deploy/proxy/templates/includes/patchpoint-app.conf.template:15, deploy/proxy/templates/includes/patchpoint-app.conf.template:17).

### FE-06: Login rate limit and lockout in the UI (last FE scenario)
- **Kind:** contract
- **Remarks:** R1.3
- **Target:** ui (`H`)
- **Preconditions:** the auth view is shown, and the FE-01 owner exists.
- **Steps:** submit „Zaloguj” 7 times without pause, with the owner's login and password `Wrong-Password-12345`.
- **Expected:**
  - Every message is one of:
    - „Invalid username or password” (backend/app/routers/auth.py:40);
    - „Too many failed login attempts. Try again later.” (backend/app/routers/auth.py:42);
    - „Too many requests, try again later” (deploy/proxy/templates/includes/patchpoint-app.conf.template:47).
  - The 7th message is one of the two 429 texts (deploy/proxy/templates/includes/patchpoint-app.conf.template:29; backend/app/routers/auth.py:94).
  - The UI never shows „Błąd serwera (HTTP …)” (frontend/app.js:110).
- **Edge cases:**
  - a) Immediately afterwards, the correct password → no app view, and the message is a 429 text (deploy/proxy/templates/includes/patchpoint-app.conf.template:47).
  - b) Wait 65 s, make 5 more wrong attempts 7 s apart, then submit the correct password → „Too many failed login attempts. Try again later.” (backend/app/routers/auth.py:94; the lockout check runs before the password verification).

## BE Test Scenarios

HTTP on the development API (`BASE=http://127.0.0.1:18100`, instance `dev`, unless stated).

### BE-01: API version in OpenAPI
- **Kind:** contract
- **Remarks:** R2.5
- **Target:** instance `docs` (`BASE=http://127.0.0.1:18102`)
- **Preconditions:** none
- **Steps:** `req GET /openapi.json`, then `req GET /docs`.
- **Expected:**
  - `/openapi.json` returns 200 with `.info.version == "0.3.0"` (backend/app/config.py:7; backend/app/main.py:80).
  - `/docs` returns 200 with `text/html` (backend/app/main.py:75).
- **Edge cases:**
  - a) On `dev`, `/openapi.json` → 404 (backend/app/config.py:18; the `docs_enabled` default is false).
  - b) `backend/pyproject.toml` has `version = "0.3.0"` (backend/pyproject.toml:3).

### BE-02: Parallel sign-up and sign-in
- **Kind:** contract
- **Remarks:** R3.8
- **Target:** instance `dev`
- **Preconditions:** `new_user` for `qa.final.$SFX.p01`…`p20`, registered one by one (201 each) (backend/app/routers/auth.py:45).
- **Steps:**
  1. Wave `be02a`, 40 jobs:
     - login of p01…p20, cookie-out `$RUN/p<NN>.jar`;
     - registration of `qa.final.$SFX.n01`…`n20` after `new_user`.
  2. Wave `be02b`, 40 jobs: each p-user sends `POST /api/tickets` twice with its jar. Body file: `{"title":"Load $SFX <job id>","description":"Parallel ticket","category":"other","priority":"low"}`.
- **Expected:**
  - `be02a`: exactly 20×200 and 20×201, and no status ≥ 500 or `000` (backend/app/routers/auth.py:45, backend/app/routers/auth.py:87).
  - `be02b`: 40×201 (backend/app/routers/tickets.py:104).
  - `SELECT COUNT(*) FROM users` → 43 (3 demo + 40) (backend/app/database.py:44).
  - `SELECT COUNT(*) FROM tickets` → 43 (3 demo + 40) (backend/app/database.py:50).
  - `$RUN/dev/api.log` has no `"event": "internal_error"` line (backend/app/main.py:26).
  - Record p50/p95/max of both waves.
- **Anchors:** auth.py `register` (hash in the threadpool before the transaction) (backend/app/routers/auth.py:48-50), auth.py `login` (backend/app/routers/auth.py:87), database.py `transaction` (backend/app/database.py:151).
- **Edge cases:**
  - a) A third wave with the same 20 logins and wrong passwords → 20×401, with no status ≥ 500 (backend/app/routers/auth.py:139).

### BE-03: Parallel wrong passwords versus the lockout
- **Kind:** contract
- **Remarks:** R3.8
- **Target:** instance `dev`
- **Preconditions:** `qa.final.$SFX.lock` is registered.
- **Steps:** wave of 20 `POST /api/auth/login` for `.lock` with `{"username": …, "password": "Wrong-Password-12345"}`.
- **Expected** (lockout check at backend/app/routers/auth.py:94 and `record_login_failure` at backend/app/routers/auth.py:108; `login_max_failures` = 5 at backend/app/config.py:25, `login_lockout_minutes` = 15 at backend/app/config.py:26):
  - exactly 5×401 „Invalid username or password” (backend/app/routers/auth.py:139);
  - 15×429 „Too many failed login attempts. Try again later.”, each with `Retry-After` `900` (backend/app/routers/auth.py:101);
  - `SELECT COUNT(*) FROM login_failures WHERE username = 'qa.final.$SFX.lock'` → 5 (backend/app/sessions.py:114).
- **Edge cases:**
  - a) The correct password afterwards → 429 (backend/app/routers/auth.py:94).
  - b) A correct login of `qa.final.$SFX.p01` → 200 (backend/app/sessions.py:104; the lockout is per username).

### BE-04: Parallel conflicting status changes
- **Kind:** contract
- **Remarks:** R3.8
- **Target:** instance `dev`
- **Preconditions:**
  - `qa.final.$SFX.emp` is registered and signed in, and creates 10 tickets one by one (201 each) (backend/app/routers/tickets.py:104).
  - `helpdesk` is signed in (jar).
- **Steps:** wave of 20 `PATCH /api/tickets/<id>` as the agent: per ticket, one `{"status":"in_progress"}` and one `{"status":"closed"}`.
- **Expected** (backend/app/routers/tickets.py:177 and the transitions at backend/app/routers/tickets.py:25):
  - Per ticket, exactly one 200 and one 400 whose detail starts with „Invalid status transition:” (backend/app/routers/tickets.py:197).
  - `GET /api/tickets/<id>` as the agent shows the status of the request that got 200 (backend/app/routers/tickets.py:158).
  - No status ≥ 500 (backend/app/main.py:103).
- **Edge cases:**
  - a) Agent `PATCH` with `{}` → 400 „Nothing to update” (backend/app/routers/tickets.py:186).
  - b) `.emp` `PATCH` → 403 „Helpdesk agent role required” (backend/app/dependencies.py:66).

### BE-05: API write during an external SQLite read transaction
- **Kind:** contract
- **Remarks:** R3.8
- **Target:** instance `dev`
- **Preconditions:**
  - `qa.final.$SFX.wal` is registered.
  - Record `sqlite3 -readonly "$RUN/dev/patchpoint.db" 'PRAGMA journal_mode'`.
  - Run edge a) first.
- **Steps**, with `t` in seconds from the start of the reader:
  1. Start a background reader: `python3` with `sqlite3.connect(db, isolation_level=None)`, `BEGIN`, `SELECT COUNT(*) FROM users`, sleep 15, `ROLLBACK`.
  2. At t≈1: `req POST /api/auth/login --data-binary @<wrong-password body for .wal>`.
  3. At t≈1.5–5.5: five `GET /api/health`, 1 s apart, each in the background with `-m 30`.
  4. At t≈7: register `qa.final.$SFX.wal2`.
  5. `wait`.
- **Expected:**
  - The login returns 401 in < 1.0 s (backend/app/routers/auth.py:139).
  - Every health request returns 200 in < 1.0 s (backend/app/routers/health.py:10).
  - The registration returns 201 in < 1.0 s (backend/app/routers/auth.py:45).
  - The API log has no `internal_error` (backend/app/main.py:26).
- **Known risk (R3.8):** in rollback-journal mode the commit waits the busy timeout on the event-loop thread (backend/app/database.py:119, backend/app/database.py:158), then fails with 500 `{"detail":"Internal server error","error_id":…}` (backend/app/main.py:21-26, backend/app/main.py:103), and every request stalls. Copy the `internal_error` lines (`exception`, `sql`) from the API log.
- **Edge cases:**
  - a) Control without the reader: the login returns 401 in < 1.0 s (backend/app/routers/auth.py:139).

### BE-06: Several processes (`WEB_CONCURRENCY=4`) versus the lockout
- **Kind:** contract
- **Remarks:** R3.8
- **Target:** instance `workers` (`BASE=http://127.0.0.1:18101`)
- **Preconditions:**
  - Instance `workers` started with `WEB_CONCURRENCY=4` in the shell prefix, `BASE=http://127.0.0.1:18101` (Makefile:22).
  - `qa.final.$SFX.mp` is registered.
- **Steps:**
  1. Count the `Started server process` lines in `$RUN/workers/api.log`.
  2. Wave of 20 wrong logins for `.mp`.
  3. `SELECT COUNT(*) FROM login_failures WHERE username = 'qa.final.$SFX.mp'` on the `workers` database.
  4. Wave of 40 registrations `qa.final.$SFX.w01`…`w40`.
- **Expected:**
  - Exactly 1 server process (Makefile:22).
  - 5×401 and 15×429 (backend/app/routers/auth.py:94, backend/app/routers/auth.py:139).
  - The count is 5 (backend/app/routers/auth.py:108).
  - 40×201, with no status ≥ 500 or `000` (backend/app/routers/auth.py:45).
- **Known risk:** uvicorn reads `WEB_CONCURRENCY` as its worker count (Makefile:22; backend/Dockerfile:44), and the per-process event loops interleave the count read and the failure write (backend/app/routers/auth.py:94, backend/app/routers/auth.py:108).
- **Edge cases:**
  - a) Control: the same 20-guess wave on `dev` gives 5×401 (backend/app/routers/auth.py:94).

### BE-07: No account-management API
- **Kind:** probe
- **Remarks:** R3.9, R1.2
- **Target:** instance `dev`
- **Remark claim:** there is no way to create an agent, to change or reset a password, or to revoke all sessions of a user.
- **Preconditions:** `helpdesk` is signed in (jar).
- **Steps**, as the agent (`helpdesk` jar):
  - `GET /api/users`
  - `POST /api/users` `{}`
  - `PATCH /api/users/1` `{"role":"agent"}`
  - `DELETE /api/users/2`
  - `POST /api/auth/password` `{}`
  - `POST /api/auth/password-reset` `{}`
  - `POST /api/auth/logout-all`
  - `DELETE /api/auth/sessions`
- **Expected:** each returns 404 `{"detail":"Not Found"}`, because only the routers `health`, `auth` and `tickets` are included (backend/app/main.py:106-108). If so → `Confirmed`.
- **Edge cases:**
  - a) `POST /api/auth/register` with a valid body for `qa.final.$SFX.escalate` plus `"role": "agent"` → 422 (backend/app/schemas.py:19). `SELECT COUNT(*) FROM users WHERE username = 'qa.final.$SFX.escalate'` → 0 (backend/app/schemas.py:18-19; `UserCreate` with `extra="forbid"`).
  - b) `SELECT username FROM users WHERE role = 'agent'` → only `helpdesk` (backend/app/database.py:45).

### BE-08: Logout ends only the current session
- **Kind:** probe
- **Remarks:** R3.9
- **Target:** instance `dev`
- **Remark claim:** after an account takeover, the other sessions of the user cannot be revoked.
- **Preconditions:** `qa.final.$SFX.multi` is registered and signed in twice, with jars A and B.
- **Steps:**
  1. `SELECT COUNT(*) FROM sessions s JOIN users u ON u.id = s.user_id WHERE u.username = 'qa.final.$SFX.multi'`.
  2. `POST /api/auth/logout` with A.
  3. `GET /api/auth/me` with A, then with B.
  4. Repeat the count.
- **Expected** (backend/app/sessions.py:88-97):
  - The first count is 2 (backend/app/routers/auth.py:142).
  - The logout returns 200 `{"message":"Logged out"}` (backend/app/routers/auth.py:172).
  - me(A) returns 401 „Not authenticated” (backend/app/dependencies.py:49).
  - me(B) returns 200 (backend/app/routers/auth.py:175).
  - The second count is 1 (backend/app/sessions.py:92).
  - If so → `Confirmed`.
- **Edge cases:**
  - a) `POST /api/auth/logout` without a cookie → 200 `{"message":"Logged out"}` (backend/app/routers/auth.py:161-172).

## OPS Test Scenarios

Containers, host and repository.

### OPS-01: Baseline gates
- **Kind:** contract
- **Remarks:** R1.2, R1.3, R1.4, R2.7
- **Target:** repository and local images
- **Preconditions:** none
- **Steps:** run the following in order, recording each with `$ <command>` and its exit code.
  1. `make lint`
  2. `make typecheck`
  3. `make test`
  4. `make semgrep` and `jq '.errors | length' reports/semgrep.json`
  5. `make trivy-fs`
  6. `make shellcheck`
  7. `make actionlint`
  8. `make ansible-lint`
  9. `docker build --no-cache --label org.opencontainers.image.source=https://github.com/l3x1cn/patchpoint --label org.opencontainers.image.revision="$(git rev-parse HEAD)" --label org.opencontainers.image.title=patchpoint-api -t patchpoint-api:local backend`
  10. `make images`
  11. `make trivy-images`
  12. `make stack-smoke`
- **Expected:**
  - Every exit code is 0 (Makefile:24-34, Makefile:45-47, Makefile:52-66, Makefile:76-82).
  - pytest reports `145 passed` (docs/faza-3-ops/dowody/README.md:8) with `TOTAL` ≥ 80% (backend/pyproject.toml:25; `--cov-fail-under=80`).
  - Semgrep reports 0 findings and `.errors | length` = 0 (scripts/scan.sh:81-86; the semgrep gate).
  - The smoke run ends with `STACK SMOKE ZAKOŃCZONY POWODZENIEM` (scripts/stack_smoke.sh:461), with 28 `[OK]` (docs/faza-3-ops/README.md:304), 0 `[BŁĄD]` (scripts/stack_smoke.sh:50) and `22 × [NAPRAWIONE]` (scripts/stack_smoke.sh:126).
- **Edge cases:** none

### OPS-02: Container hardening of the running stack
- **Kind:** contract
- **Remarks:** R1.3
- **Target:** stack `patchpoint-final`
- **Preconditions:** the `patchpoint-final` stack is up (Setup).
- **Steps:**
  - `docker inspect` of `patchpoint-final-api-1` and `patchpoint-final-proxy-1`;
  - `docker compose exec -T proxy id -u`;
  - `docker network inspect patchpoint-final_backend -f '{{.Internal}}'`;
  - `docker compose port api 8000`.
- **Expected** (compose.yaml:17-93, services and networks):
  - **api:**
    - `Config.User` `10001:10001` (backend/Dockerfile:38), `ReadonlyRootfs` true (compose.yaml:39), `CapDrop` `["ALL"]` (compose.yaml:40-41), `SecurityOpt` `["no-new-privileges:true"]` (compose.yaml:42-43);
    - `Memory` 1073741824 (compose.yaml:44), `NanoCpus` 1000000000 (compose.yaml:45), `PidsLimit` 256 (compose.yaml:46);
    - `LogConfig` json-file with `max-size` 10m and `max-file` 5 (compose.yaml:11-15, compose.yaml:47);
    - only network `patchpoint-final_backend` (compose.yaml:37-38), and no published port (empty or `:0`) (compose.yaml:18-47; the api service has no `ports`).
  - **proxy:**
    - `Config.User` `nginx` with uid 101 (deploy/proxy/Dockerfile:57), `ReadonlyRootfs` false (docs/faza-3-ops/README.md:313), `CapDrop` `["ALL"]` (compose.yaml:75-76), `no-new-privileges:true` (compose.yaml:77-78);
    - `Memory` 268435456 (compose.yaml:79), `NanoCpus` 500000000 (compose.yaml:80), `PidsLimit` 128 (compose.yaml:81);
    - the same logging (compose.yaml:82);
    - networks `patchpoint-final_edge` and `patchpoint-final_backend` (compose.yaml:69-72), and ports `127.0.0.1:28080` and `127.0.0.1:28443` (compose.yaml:55-57).
  - The `backend` network has `Internal` true (compose.yaml:86-87).
- **Edge cases:** none

### OPS-03: TLS protocols and ciphers
- **Kind:** contract
- **Remarks:** R1.3
- **Target:** stack `patchpoint-final`, HTTPS on 28443
- **Preconditions:** the `patchpoint-final` stack is up (Setup).
- **Steps:** `openssl s_client -connect 127.0.0.1:28443 -servername patchpoint.localhost -CAfile deploy/proxy/dev-tls/fullchain.pem </dev/null`, once with each option set below.
  - `-tls1_3`
  - `-tls1_2 -cipher ECDHE-ECDSA-AES128-GCM-SHA256`
  - `-tls1_2 -cipher ECDHE-ECDSA-AES128-SHA`
  - `-tls1_1 -cipher 'DEFAULT:@SECLEVEL=0'`
  - Then, separately: `curl -s --noproxy '*' -o /dev/null "$S/api/health"` without `--cacert`.
- **Expected** (docs/faza-3-ops/README.md:135, the TLS bullet of §6):
  - The first two complete the handshake: protocol TLSv1.3 and TLSv1.2, `Verify return code: 0 (ok)` (docs/faza-3-ops/README.md:135).
  - The third and fourth fail with a non-zero exit (docs/faza-3-ops/README.md:135; TLS 1.2 and 1.3 with AEAD ciphers only).
  - curl exits with 60 (docs/testing/plans/2026-11-27-patchpoint-phase-3-ops-test-plan.md:56).
- **Edge cases:** none

### OPS-04: Security events in the logs
- **Kind:** contract
- **Remarks:** R1.2, R3.10
- **Target:** stack `patchpoint-final`, `BASE=$H`
- **Preconditions:**
  - 65 s have passed since FE-06.
  - `new_user` has run for `qa.final.$SFX.log1` and `.log2`.
  - All requests use `BASE=$H`.
- **Steps:**
  1. Register `.log1`.
  2. Register `.log1` again.
  3. Five wrong logins as `.log1`.
  4. A sixth wrong login as `.log1`.
  5. A login as the unregistered `qa.final.$SFX.ghost`.
  6. Register `.log2` and sign in.
  7. `GET /api/auth/me` with `-H "Cookie: session=forged-$SFX"`.
  8. `.log2`: `GET /api/tickets/1`.
  9. `.log2`: `PATCH /api/tickets/1` `{"status":"closed"}`.
  10. `.log2` creates a ticket; `helpdesk` signs in and `PATCH`es it to `{"status":"in_progress"}`.
  11. `.log2`: `POST /api/tickets` `{"title":""}`.
  12. `.log2` logs out.
  13. `POST /api/auth/logout` with `-H 'Origin: https://evil.example'`.
  14. `GET /api/tickets?search=1' OR '1'='1`, then a registration with `full_name` `<script>alert(1)</script>`.
  15. 8 parallel logins as `.ghost`.
  16. `docker compose logs --no-color api > "$RUN/api-stack.log"`, and the same for `proxy`.
- **Expected** statuses, step by step:
  - 1: 201 (backend/app/routers/auth.py:45)
  - 2: 409 (backend/app/routers/auth.py:65)
  - 3: 401×5 (backend/app/routers/auth.py:139)
  - 4: 429 (backend/app/routers/auth.py:100)
  - 5: 401 (backend/app/routers/auth.py:125)
  - 6: 201, 200 (backend/app/routers/auth.py:45, backend/app/routers/auth.py:87)
  - 7: 401 (backend/app/dependencies.py:49)
  - 8: 404 (backend/app/routers/tickets.py:99)
  - 9: 403 (backend/app/dependencies.py:66)
  - 10: 201, 200, 200 (backend/app/routers/tickets.py:104, backend/app/routers/tickets.py:177)
  - 11: 422 (backend/app/schemas.py:90)
  - 12: 200 (backend/app/routers/auth.py:172)
  - 13: 403 „Origin not allowed” (backend/app/middleware.py:69)
  - 14: 403 and 403 „Request blocked by the proxy” (deploy/proxy/templates/includes/patchpoint-app.conf.template:41)
  - 15: at least one 429 „Too many requests, try again later” (deploy/proxy/templates/includes/patchpoint-app.conf.template:47)
- **Expected** API log: one JSON line per event (backend/app/audit.py:31-32; `log_security_event`). Every `client_ip` is the same address, and it is not `10.253.0.10` (compose.yaml:26; `FORWARDED_ALLOW_IPS`). The events:
  - `user_registered` with role `employee` (backend/app/routers/auth.py:76)
  - `registration_conflict` (backend/app/routers/auth.py:63)
  - `login_failed` with reason `bad_password`, 5 times (backend/app/routers/auth.py:137)
  - `login_blocked` (backend/app/routers/auth.py:96)
  - `login_failed` with reason `unknown_user` (backend/app/routers/auth.py:123)
  - `login_succeeded` (backend/app/routers/auth.py:152)
  - `session_rejected` with reason `unknown` (backend/app/dependencies.py:43, backend/app/dependencies.py:46)
  - `access_denied` with reason `not_ticket_owner` and ticket id 1 (backend/app/routers/tickets.py:95)
  - `access_denied` with reason `agent_role_required` (backend/app/dependencies.py:62)
  - `ticket_updated` (backend/app/routers/tickets.py:221)
  - `validation_failed`, with field names and types only (backend/app/main.py:51)
  - `logout` (backend/app/routers/auth.py:170)
- **Expected** proxy log:
  - ModSecurity audit JSON with `ruleId` 942… and 941… (deploy/proxy/Dockerfile:40-42);
  - an nginx `limiting requests` warning (deploy/proxy/templates/conf.d/patchpoint-limits.conf.template:5).
- **Expected** hygiene: `grep -F -f "$RUN/secrets.txt"` over both logs returns nothing (deploy/proxy/Dockerfile:42; the audit log has no parts B, I and J, and backend/app/audit.py:30 forbids secrets in event fields).
- **Observation** for R3.10 (no verdict of its own):
  - Whether step 13 left any log line. `OriginCheckMiddleware` in backend/app/middleware.py logs nothing (backend/app/middleware.py:48-70).
  - compose.yaml has no log shipper, so the logs stay local (docs/faza-3-ops/README.md:260; §10).
- **Edge cases:** none

### OPS-05: Parallel logins versus the API memory limit
- **Kind:** contract
- **Remarks:** R3.8
- **Target:** stack `patchpoint-final`, network `patchpoint-final_backend`
- **Preconditions:** a fresh stack, and `RC0=$(docker inspect -f '{{.RestartCount}}' patchpoint-final-api-1)`.
- **Steps:**
  1. In `$RUN/oom/`, create 40 registration bodies `reg.<n>.json` and 40 login bodies `login.<n>.json` for `qa.final.$SFX.m01`…`m40`, using the same jq-over-stdin pattern as `new_user`.
  2. Run the client:
     ```bash
     docker run --rm --network patchpoint-final_backend --user "$(id -u):$(id -g)" -v "$RUN/oom:/work" \
       curlimages/curl@sha256:3fb7e13e5d179a845c97d78204f3f1064d1907037f26a3ebf91710571151fd93 sh -c '
       cd /work
       for f in reg.*.json; do curl -s -o /dev/null -w "%{http_code}\n" -H "Content-Type: application/json" --data-binary "@$f" http://api:8000/api/auth/register >> reg.out; done
       for f in login.*.json; do (curl -s -o /dev/null -m 120 -w "%{http_code} %{time_total}\n" -H "Content-Type: application/json" --data-binary "@$f" http://api:8000/api/auth/login >> login.out) & done
       wait'
     ```
  3. While the login loop runs, sample `docker stats --no-stream --format '{{.MemUsage}}' patchpoint-final-api-1` every 0.5 s into `$RUN/oom/mem.txt`.
  4. Afterwards: `docker inspect -f '{{.State.OOMKilled}} {{.RestartCount}} {{.State.Status}}' patchpoint-final-api-1`.
- **Expected:**
  - 40×201 for the registrations (backend/app/routers/auth.py:45).
  - 40×200 for the logins, with no `000` and no status ≥ 500 (backend/app/routers/auth.py:87, backend/app/routers/auth.py:127).
  - `false <RC0> running` (compose.yaml:20, compose.yaml:44).
  - The highest sampled memory is < 1GiB (compose.yaml:44; `mem_limit: 1g`).
- **Known risk:** `PasswordHasher()` defaults use 64 MiB per hash (backend/app/security.py:11), and up to 40 hashes run at once in the threadpool (backend/app/routers/auth.py:48, backend/app/routers/auth.py:127).
- **Edge cases:**
  - a) Through the proxy from one IP: 12 parallel wrong logins return only 401 or 429, with no 502 or 504 (deploy/proxy/templates/includes/patchpoint-app.conf.template:29; `limit_req` on login).

### OPS-06: API restart after the process exits
- **Kind:** contract
- **Remarks:** R1.3
- **Target:** stack `patchpoint-final`
- **Preconditions:**
  - `helpdesk` is signed in through `H` (jar).
  - `N0` = the number of tickets in `GET /api/tickets?limit=100`.
  - The `RestartCount` of api and of proxy are recorded.
- **Steps:**
  1. `docker compose exec -T api python -c "import os, signal; os.kill(1, signal.SIGTERM)"`.
  2. Every 1 s for 90 s, run `curl -s --noproxy '*' -m 10 -o /dev/null -w '%{http_code} %{time_total}\n' "$H/api/health"`.
- **Expected** (compose.yaml:20 `restart: unless-stopped` and volume `api-data` at compose.yaml:32; deploy/proxy/templates/includes/patchpoint-proxy.conf.template:5, variable `proxy_pass`):
  - 200 again within 60 s (compose.yaml:20).
  - During the outage only 502 or 504, and no request takes longer than 10 s (deploy/proxy/templates/includes/patchpoint-proxy.conf.template:4-5).
  - The api `RestartCount` is +1, and the proxy count is unchanged (compose.yaml:20, compose.yaml:51).
  - After a new agent login, the ticket count equals `N0` (compose.yaml:32, compose.yaml:93).
- **Edge cases:** none

### OPS-07: Hung proxy
- **Kind:** probe
- **Remarks:** R3.5
- **Target:** stack `patchpoint-final`
- **Remark claim:** an unhealthy proxy is not restarted automatically (docs/faza-3-ops/README.md:317, the nginx bullet of §13).
- **Preconditions:** the `patchpoint-final` stack is up (Setup).
- **Steps:**
  1. `docker compose exec -T proxy sh -c 'pkill -STOP -f "nginx: worker process"'`. If `pkill` is missing: `for p in $(ps -o pid,args | awk '/nginx: worker process/ && !/awk/ {print $1}'); do kill -STOP "$p"; done`.
  2. Confirm the workers are in state `T` with `ps -o pid,stat,args`.
  3. Every 10 s for 180 s, record:
     - `docker inspect -f '{{.State.Health.Status}} {{.RestartCount}} {{.State.Status}}' patchpoint-final-proxy-1`;
     - `curl -s --noproxy '*' -m 5 -o /dev/null -w '%{http_code}' "$H/api/health"; echo " exit=$?"`.
  4. `docker compose restart proxy`, then poll `/api/health` for up to 60 s.
- **Expected:** `Confirmed` if
  - the health status reaches `unhealthy` (deploy/proxy/Dockerfile:60-61);
  - `RestartCount` does not change and `Status` stays `running` (compose.yaml:51; docs/faza-3-ops/README.md:317);
  - curl exits with 28 until the manual restart (docs/faza-3-ops/README.md:317);
  - after the restart, `/api/health` returns 200 within 60 s (docs/faza-3-ops/README.md:317).
- **Edge cases:** none

### OPS-08: Container egress
- **Kind:** probe and contract
- **Remarks:** R3.6, R1.3
- **Target:** stack `patchpoint-final`
- **Remark claim:** the proxy has unrestricted Internet egress (docs/faza-3-ops/README.md:314, the egress bullet of §13).
- **Preconditions:** the `patchpoint-final` stack is up (Setup).
- **Steps:**
  1. Host control: `curl -s --noproxy '*' -m 10 -o /dev/null -w '%{http_code}' https://www.google.com/generate_204`.
  2. `docker compose exec -T proxy curl -s -m 10 -o /dev/null -w '%{http_code}' https://www.google.com/generate_204`.
  3. `docker compose exec -T api python -c "import socket; socket.create_connection(('1.1.1.1', 443), timeout=5)"`, recording the exit code.
- **Expected:**
  - `Confirmed` if the proxy gets 204 (docs/faza-3-ops/README.md:314; compose.yaml:85).
  - Contract: the API connection fails (compose.yaml:86-87; the `backend` network is `internal`).
  - `Need info` if the host control fails.
- **Edge cases:** none

### OPS-09: SQLite backup per §10
- **Kind:** contract
- **Remarks:** R3.7
- **Target:** stack `patchpoint-final`
- **Preconditions:** the OPS-05 data, plus a ticket with one comment by `.m01` created through `H`.
- **Steps:**
  1. Run the three commands of docs/faza-3-ops/README.md §10 (`:265-267`), with `--project-directory /opt/patchpoint` replaced by the stack environment above, and copy the file to `$RUN/backup/patchpoint.db`.
  2. `sqlite3 "$RUN/backup/patchpoint.db" 'PRAGMA integrity_check'`.
  3. Count `users`, `tickets` and `comments` in the backup (`sqlite3 -readonly`) and in the live database (`docker compose exec -T api python -c` with `sqlite3.connect('file:/data/patchpoint.db?mode=ro', uri=True)`).
- **Expected:**
  - All three commands exit with 0 (docs/faza-3-ops/README.md:265-267).
  - The integrity check prints `ok` (docs/faza-3-ops/README.md:262).
  - The counts are equal (docs/faza-3-ops/README.md:262).
  - `/data/backup.db` no longer exists afterwards (docs/faza-3-ops/README.md:267).
- **Edge cases:** none

### OPS-10: Restore drill and data persistence
- **Kind:** contract
- **Remarks:** R3.7
- **Target:** stack `patchpoint-final`
- **Preconditions:** OPS-09 has produced `$RUN/backup/patchpoint.db`.
- **Steps:**
  - a) `docker compose down`, then `docker compose up -d --wait --wait-timeout 180`. Recount, and sign in as `.m01`.
  - b) As `.m01`, create the ticket `restore-marker-$SFX`. Then run the restore procedure:
    ```bash
    docker compose down
    docker volume rm patchpoint-final_api-data
    install -d -m 0755 "$RUN/restore"
    install -m 0644 "$RUN/backup/patchpoint.db" "$RUN/restore/patchpoint.db"
    docker compose run --rm --no-deps -T -v "$RUN/restore:/restore:ro" --entrypoint python api -c "import shutil; shutil.copyfile('/restore/patchpoint.db', '/data/patchpoint.db')"
    rm -rf "$RUN/restore"
    docker compose up -d --wait --wait-timeout 180
    ```
- **Expected:**
  - a) The counts are unchanged, and the `.m01` login returns 200 (compose.yaml:32, compose.yaml:93; the data lives in the volume `api-data`).
  - b) The stack is healthy and the counts equal the backup counts (docs/faza-3-ops/README.md:270; the restore procedure is not described there). `.m01` searching for `restore-marker-$SFX` finds nothing (backend/app/routers/tickets.py:148), and the `.m02` login returns 200 (backend/app/routers/auth.py:87).
- **Edge cases:** none

### OPS-11: Secrets in the git history
- **Kind:** probe and contract
- **Remarks:** R3.3
- **Target:** repository
- **Remark claim:** secrets are scanned only in the current tree, and nothing scans the history (scripts/scan.sh:102, `fs` with `--scanners vuln,secret,misconfig`; `.git` is skipped at scripts/scan.sh:25).
- **Preconditions:** none
- **Steps:**
  1. Run gitleaks:
     ```bash
     docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD:/repo:ro" -v "$RUN/gl:/out" \
       zricethezav/gitleaks:v8.30.1@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f \
       git --log-opts=--all --redact --report-format json --report-path /out/gitleaks.json /repo
     ```
     Exit code 0 means no leaks and 1 means leaks. If the `git` subcommand is unknown, use `detect --source /repo --log-opts=--all --redact --report-format json --report-path /out/gitleaks.json` instead.
  2. `grep -nE 'gitleaks|trufflehog' .github/workflows/ci.yml scripts/scan.sh`.
  3. `git log --all --format=%h -- .av/secrets.local.env .api.env .env deploy/ansible/inventory.yml deploy/ansible/group_vars/patchpoint/vault.yml`.
  4. `gh repo view --json visibility --jq .visibility`.
- **Expected:**
  - Contract: the `git log` output is empty (.gitignore:17, .gitignore:21-22, .gitignore:24-25).
  - `Confirmed` if the grep is empty (scripts/scan.sh:102).
  - Every gitleaks finding is triaged with its rule, file, short commit and classification: `true positive` or `false positive: <reason>`. A true positive is a HIGH QA issue: rotate the secret, do not rewrite the history.
  - Copy the redacted report to `$EVD/gitleaks.json`.
- **Edge cases:** none

### OPS-12: IaC scan of compose, Dockerfiles, Ansible and workflows
- **Kind:** probe
- **Remarks:** R3.4
- **Target:** repository
- **Remark claim:** compose.yaml and Ansible are not covered by an IaC scanner. Trivy `misconfig` covers the Dockerfiles only (docs/faza-3-ops/dowody/README.md:11, trivy-fs row).
- **Preconditions:** none
- **Steps:**
  1. Run KICS:
     ```bash
     docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/path:ro" -v "$RUN/kics:/out" \
       checkmarx/kics:v2.2.1@sha256:49ccc54b6ae7f5d5fc95e96f8f95c18c57f3bba047ab611a03d80792bdff6757 \
       scan -p /path/compose.yaml,/path/backend/Dockerfile,/path/deploy/proxy/Dockerfile,/path/deploy/ansible,/path/.github/workflows \
       --exclude-paths /path/deploy/ansible/tools,/path/deploy/ansible/.ansible \
       -o /out --output-name kics --report-formats json --ignore-on-exit results
     ```
     If a flag is rejected, read `kics scan --help` and keep the same semantics.
  2. Write `severity_counters` and every HIGH and MEDIUM query (name, file, line) to `$EVD/kics-summary.txt`.
  3. `grep -nE 'kics|checkov' .github/workflows/ci.yml`.
- **Expected:**
  - `Confirmed` if the grep is empty (scripts/scan.sh:102; docs/faza-3-ops/dowody/README.md:11).
  - Every HIGH and MEDIUM finding is classified as `documented (§ ref)`, `false positive: <reason>` or `new defect`. A `new defect` becomes a QA issue and is not fixed here.
- **Edge cases:** none

### OPS-13: Semgrep without network
- **Kind:** probe
- **Remarks:** R3.2
- **Target:** repository, Semgrep container without network
- **Remark claim:** the rule packs are fetched from the registry at scan time (scripts/scan.sh:24, scripts/scan.sh:68).
- **Preconditions:** none
- **Steps:** the arguments of scripts/scan.sh (semgrep branch, scripts/scan.sh:71-74) plus `--network none`:
  ```bash
  mkdir -p "$RUN/sg"
  docker run --rm --network none --user "$(id -u):$(id -g)" -e HOME=/tmp -e SEMGREP_SEND_METRICS=off \
    -v "$PWD:/src:ro" -v "$RUN/sg:/reports" -w /src \
    semgrep/semgrep:1.185.0@sha256:67518c174185a2043fdbed16c70631b79209499b3671178e7194379b48295a0d \
    semgrep scan --metrics=off --error --config p/python --config p/javascript --config p/dockerfile \
    --config p/docker-compose --config p/github-actions --config p/owasp-top-ten --json-output=/reports/semgrep.json .
  ```
  Record the exit code and the error lines.
- **Expected:**
  - `Confirmed` if the exit code is not 0 and the output names a failed configuration download (scripts/scan.sh:24, scripts/scan.sh:73).
- **Edge cases:** none

### OPS-14: Supply chain, static checks
- **Kind:** contract and probe
- **Remarks:** R1.4, R3.1, R3.3
- **Target:** repository
- **Remark claim:** the images get no SBOM or signature, and no scan runs on a schedule (docs/faza-3-ops/README.md:319, .github/workflows/ci.yml:19-22).
- **Preconditions:** none
- **Steps:**
  1. Contract checks: list the `^FROM` lines of backend/Dockerfile and deploy/proxy/Dockerfile, the `*_IMAGE="…"` lines of scripts/scan.sh, the `uses:` lines of .github/workflows/ci.yml and the content lines of `.trivyignore`.
  2. Probes:
     - `grep -nE '^\s*schedule:' .github/workflows/ci.yml`;
     - `grep -niE 'sbom|syft|cosign|attest' .github/workflows/ci.yml`;
     - an anonymous token request to `https://ghcr.io/token?scope=repository:l3x1cn/patchpoint/api:pull`;
     - `gh run view 44694936930 --job <publish job id> --log`.
- **Expected:**
  - Contract checks:
    - Every `^FROM` line in backend/Dockerfile and deploy/proxy/Dockerfile contains `@sha256:` (backend/Dockerfile:6, backend/Dockerfile:8, backend/Dockerfile:20; deploy/proxy/Dockerfile:7, deploy/proxy/Dockerfile:20).
    - Every `*_IMAGE="…"` line in scripts/scan.sh contains `@sha256:` (scripts/scan.sh:20-23).
    - Every `uses:` in .github/workflows/ci.yml ends with `@<40 hex> # v…` (.github/workflows/ci.yml:47).
    - `.trivyignore` has no line that is neither a comment nor blank (.trivyignore:1-8).
  - Probes:
    - `grep -nE '^\s*schedule:' .github/workflows/ci.yml` is empty → R3.3, scheduled scans: `Confirmed` (.github/workflows/ci.yml:19-22).
    - `grep -niE 'sbom|syft|cosign|attest' .github/workflows/ci.yml` is empty → R3.1: `Confirmed` (docs/faza-3-ops/README.md:319).
    - An anonymous token request to `https://ghcr.io/token?scope=repository:l3x1cn/patchpoint/api:pull` returns no token; record it, since the packages are private (deploy/ansible/roles/patchpoint/tasks/main.yml:97-100).
    - The two `digest: sha256:…` lines of `gh run view 44694936930 --job <publish job id> --log` are recorded (.github/workflows/ci.yml:177-179).
- **Edge cases:** none

### OPS-15: Documentation consistency
- **Kind:** contract
- **Remarks:** R2.4, R2.6
- **Target:** repository and GitHub
- **Preconditions:** `.gitignore` carries the root-anchored `/reports/` rule (Task 1).
- **Steps:**
  - `gh repo view --json visibility` agrees with the comment at `.github/workflows/ci.yml:13-15` (.github/workflows/ci.yml:14).
  - docs/faza-3-ops/README.md `:319` and `:328` agree with run 44694936930 (docs/faza-3-ops/README.md:319, docs/faza-3-ops/README.md:328). The publish job's conclusion comes from `gh run view 44694936930 --json jobs`.
  - `git ls-files` lists `docs/testing/plans/2026-11-27-patchpoint-phase-3-ops-test-plan.md` and `docs/testing/reports/2026-11-27-patchpoint-phase-3-ops-report.md` (docs/faza-3-ops/README.md:308).
  - `docs/faza-3-ops/dowody/ci.md` mentions 44694936930 (docs/faza-3-ops/dowody/ci.md:23).
  - `git check-ignore -q docs/testing/reports/x.md` exits with 1 (Task 1) (.gitignore:20).
- **Expected:** everything agrees (each check above).
- **Predicted:** the first two checks disagree → `Fail` (LOW) → fix B5.
- **Edge cases:** none

### OPS-16: Ansible, static checks
- **Kind:** contract and probe
- **Remarks:** R2.1, R3.7
- **Target:** `deploy/ansible`
- **Remark claim:** SSH is open to the Internet by default and nothing like fail2ban or sshguard limits brute force (deploy/ansible/roles/base/defaults/main.yml:11-14, docs/faza-3-ops/README.md:83).
- **Preconditions:** none
- **Steps**, from `deploy/ansible`:
  1. Render the firewall template with the role defaults:
     ```bash
     uv run --locked --python 3.13 --project tools ansible localhost -i localhost, -c local -m ansible.builtin.template \
       -a "src=roles/base/templates/nftables.conf.j2 dest=$RUN/nft/defaults.conf" -e @roles/base/defaults/main.yml
     ```
  2. Render it again with `-e '{"base_ssh_allowed_ipv4": ["198.51.100.0/24"], "base_ssh_allowed_ipv6": []}'` into `example.conf`. These are the values of `deploy/ansible/inventory.example.yml`.
  3. Validate both renders:
     ```bash
     docker run --rm --cap-add NET_ADMIN -v "$RUN/nft:/nft:ro" debian:trixie-slim \
       sh -c 'apt-get update -qq && apt-get install -y -qq nftables >/dev/null && nft -c -f /nft/defaults.conf && nft -c -f /nft/example.conf'
     ```
  4. Run the `argv` of the task „Utwórz tymczasowy certyfikat TLS do pierwszego startu proxy” (deploy/ansible/roles/patchpoint/tasks/main.yml:62-87) for `helpdesk.example.com`, writing into `$RUN/tls/`, and inspect it with `openssl x509 -noout -ext subjectAltName,basicConstraints,extendedKeyUsage`.
  5. `grep -rniE 'fail2ban|sshguard|crowdsec' deploy/ README.md docs/faza-3-ops/README.md`.
- **Expected:**
  - Contract:
    - Both renders and both `nft -c` runs exit with 0 (deploy/ansible/roles/base/templates/nftables.conf.j2:8-10).
    - `example.conf` contains `ip saddr { 198.51.100.0/24 } tcp dport 22 accept` and no `ip6 saddr` (deploy/ansible/roles/base/templates/nftables.conf.j2:19-24; deploy/ansible/inventory.example.yml:13-15).
    - The certificate has `DNS:helpdesk.example.com` (deploy/ansible/roles/patchpoint/tasks/main.yml:78), a `critical` `CA:FALSE` (deploy/ansible/roles/patchpoint/tasks/main.yml:80) and `TLS Web Server Authentication` (deploy/ansible/roles/patchpoint/tasks/main.yml:82) (R2.1).
  - Probes (R3.7):
    - `defaults.conf` contains `ip saddr { 0.0.0.0/0 } tcp dport 22 accept` and `ip6 saddr { ::/0 } tcp dport 22 accept` → „SSH open to the Internet by default”: `Confirmed`, documented in §4 (deploy/ansible/roles/base/defaults/main.yml:11-14; docs/faza-3-ops/README.md:83).
    - The grep is empty → „no fail2ban/sshguard”: `Confirmed` (docs/faza-3-ops/README.md:83).
- **Edge cases:** none

### OPS-17: Ansible roles `base` and `docker` on a systemd container
- **Kind:** contract
- **Remarks:** R2.2, R2.3, R3.7
- **Target:** container `pp-ansible-target` (Debian 13 with systemd)
- **Preconditions**, in `$RUN/at/`:
  1. `ssh-keygen -q -t ed25519 -N '' -f "$RUN/at/id_ed25519"`, and write this Dockerfile:
     ```dockerfile
     FROM debian:trixie
     ENV container=docker
     RUN apt-get update \
      && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends systemd systemd-sysv dbus openssh-server sudo python3 python3-apt ca-certificates iproute2 procps \
      && rm -rf /var/lib/apt/lists/* \
      && useradd -m -s /bin/bash admin \
      && printf 'admin ALL=(ALL) NOPASSWD:ALL\n' > /etc/sudoers.d/admin && chmod 0440 /etc/sudoers.d/admin \
      && install -d -m 0700 -o admin -g admin /home/admin/.ssh \
      && systemctl enable ssh
     COPY --chown=admin:admin --chmod=0600 id_ed25519.pub /home/admin/.ssh/authorized_keys
     STOPSIGNAL SIGRTMIN+3
     CMD ["/sbin/init"]
     ```
  2. Build and start the target:
     ```bash
     docker build -t pp-ansible-target:test "$RUN/at"
     docker run -d --name pp-ansible-target --hostname pp-ansible-target --privileged --cgroupns=private \
       -e container=docker --tmpfs /run --tmpfs /run/lock -v pp-ansible-docker:/var/lib/docker \
       -p 127.0.0.1:2222:22 pp-ansible-target:test
     ```
  3. Wait until `docker exec pp-ansible-target systemctl is-system-running` prints `running` or `degraded`, for at most 120 s.
  4. Write the inventory `$RUN/at/inventory.yml`:
     - group `patchpoint`, host `pp-ansible-target`;
     - `ansible_host: 127.0.0.1`, `ansible_port: 2222`, `ansible_user: admin`;
     - `ansible_ssh_private_key_file: <$RUN>/at/id_ed25519`;
     - `ansible_ssh_common_args: "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes"`.
  5. Write the playbook `$RUN/at/site-test.yml`: `hosts: patchpoint`, `become: true`, roles `base` and `docker`.
  6. The collections are already installed by `make ansible-lint` (Makefile:79-82).
- **Steps:**
  - a) First run, from `deploy/ansible`:
    ```bash
    ANSIBLE_ROLES_PATH=roles ANSIBLE_COLLECTIONS_PATH=.ansible/collections \
      uv run --locked --python 3.13 --project tools ansible-playbook -i "$RUN/at/inventory.yml" "$RUN/at/site-test.yml"
    ```
  - b)–i) The checks below, run with `docker exec pp-ansible-target …`.
  - j) A second run of the same playbook.
  - Teardown: `docker rm -f pp-ansible-target`, `docker volume rm pp-ansible-docker`, `docker rmi pp-ansible-target:test`.
- **Expected:**
  - a) The recap shows `failed=0` and `unreachable=0` (deploy/ansible/roles/base/handlers/main.yml:11-14).
  - b) In the output of run 1, `RUNNING HANDLER [base : Przeładuj konfigurację systemd]` comes before `RUNNING HANDLER [base : Przeładuj nftables]` (deploy/ansible/roles/base/handlers/main.yml:7, deploy/ansible/roles/base/handlers/main.yml:11).
  - c) `systemctl show nftables -p DropInPaths -p ExecStop` lists `/etc/systemd/system/nftables.service.d/10-patchpoint.conf`, and `nft delete table inet patchpoint_host` with `ignore_errors=yes` (deploy/ansible/roles/base/tasks/main.yml:58, deploy/ansible/roles/base/tasks/main.yml:69; the drop-in task).
  - d) `systemctl is-active nftables ssh docker` prints `active` three times (deploy/ansible/roles/base/tasks/main.yml:75-79). `nft list table inet patchpoint_host` shows `policy drop` and `tcp dport 22 accept` (deploy/ansible/roles/base/templates/nftables.conf.j2:10, deploy/ansible/roles/base/templates/nftables.conf.j2:19-24).
  - e) `N1=$(nft list ruleset | grep -c 'chain DOCKER')` is greater than 0. After `systemctl restart nftables`, the same count equals `N1` (deploy/ansible/roles/base/tasks/main.yml:63-69).
  - f) `nft delete table inet patchpoint_host; systemctl stop nftables` exits with 0, and `systemctl show -p Result nftables` prints `Result=success` (deploy/ansible/roles/base/tasks/main.yml:68-69). `systemctl start nftables` restores the table (deploy/ansible/roles/base/templates/nftables.conf.j2:5-8).
  - g) `sshd -T` contains `permitrootlogin no`, `passwordauthentication no`, `kbdinteractiveauthentication no`, `x11forwarding no`, `allowtcpforwarding no` and `maxauthtries 3` (deploy/ansible/roles/base/templates/sshd-patchpoint.conf.j2:3-10).
  - h) Start `docker exec -d pp-ansible-target python3 -m http.server 8081`. Read the target IP with `docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' pp-ansible-target`. Then `docker run --rm alpine:3.24 sh -c 'nc -z -w 3 <ip> 8081; echo "8081:$?"; nc -z -w 3 <ip> 22; echo "22:$?"'` prints `8081:1` and `22:0` (deploy/ansible/roles/base/templates/nftables.conf.j2:10, deploy/ansible/roles/base/templates/nftables.conf.j2:19-24). If BusyBox `nc` rejects `-z`, run `apk add --no-cache netcat-openbsd` first.
  - i) `/etc/apt/apt.conf.d/20auto-upgrades` contains `APT::Periodic::Update-Package-Lists "1";` and `APT::Periodic::Unattended-Upgrade "1";` (deploy/ansible/roles/base/templates/20auto-upgrades.j2:2-3). `apt-config dump` contains `origin=Docker,label=Docker CE` (deploy/ansible/roles/docker/tasks/main.yml:34).
  - j) The recap of run 2 shows `changed=0` and `failed=0` (deploy/ansible/roles/base/tasks/main.yml:18, deploy/ansible/roles/docker/tasks/main.yml:17-21).
- **`Need info`** (named reason) if:
  - the target never reaches `running` or `degraded` within 120 s; or
  - `journalctl -u docker` in the target shows a storage or cgroup error that is unrelated to the roles.
- **Edge cases:** none

### OPS-18: CI on GitHub
- **Kind:** contract
- **Remarks:** R1.4, R2.6, R2.7
- **Target:** GitHub Actions, workflow `CI`
- **Preconditions:** the delivery branch holds the commits of Tasks 1–12.
- **Steps** (Task 13):
  1. Push the delivery branch and open a draft PR to `main`.
  2. Wait for the `CI` workflow run for the pushed head SHA, with event `pull_request`.
- **Expected** (.github/workflows/ci.yml:40-179, jobs):
  - The run concludes with `success` (.github/workflows/ci.yml:19-22).
  - `quality`, `semgrep`, `trivy-fs`, `ansible`, `scripts` and `build` are `success` (.github/workflows/ci.yml:41, .github/workflows/ci.yml:62, .github/workflows/ci.yml:79, .github/workflows/ci.yml:96, .github/workflows/ci.yml:110, .github/workflows/ci.yml:122-123).
  - `publish` is `skipped` (.github/workflows/ci.yml:177-179).
- **Edge cases:** none

## Out of harness scope
- VPS: issuing the Let's Encrypt certificate (role `letsencrypt`) — needs a public host with a domain and reachable port 80.
- Logging in to GHCR and deploying by digest (role `patchpoint`) — needs a server and a GHCR token with package read access.
- DAST and load tests beyond the probes OPS-05 and BE-02 — no load generator (hey, wrk, ab) is installed, and the single-host stack is not a load-test target.
