# Testy końcowe PatchPoint z weryfikacją uwag prowadzącego i naprawą potwierdzonych błędów

## Kontekst

Prośba: plan przetestowania całej aplikacji, który uwzględnia ocenę prowadzącego. Ocena ma trzy części: „Co wyszło naprawdę dobrze”, „Rzeczy do posprzątania” (wykonane w commicie `0f8dbc8`) i „Co warto rozwinąć”. Decyzje użytkownika:

1. **Naprawy.** Potwierdzone błędy naprawiamy w tej delivery. Nie dodajemy nowych funkcji z sekcji 3 oceny: IAM, SBOM i podpisów, harmonogramu CI, skanów historii i IaC w CI, auto-restartu, filtra egress, fail2ban, automatycznych kopii ani wysyłki logów.
2. **Ansible.** Testujemy go na lokalnym kontenerze systemd.
3. **CI.** Uruchamiamy je przez push gałęzi delivery i draft PR.

Stan końcowy, wszystko w repozytorium:

- plan testów i dowody;
- raport końcowy z macierzą uwag prowadzącego i porównaniem przed/po poprawkach;
- poprawki potwierdzonych błędów z testami regresji;
- odświeżone dowody Fazy 3;
- przebieg CI na draft PR.

Ustalenia z kodu, na których opiera się plan:

- **SQLite w pętli zdarzeń.**
  - Wszystkie trasy to `async def`. SQLite działa synchronicznie w wątku pętli zdarzeń (`get_db` w `backend/app/dependencies.py`), więc w jednym procesie transakcje się nie przeplatają.
  - `connect()` (`backend/app/database.py:118-122`) nie ustawia `journal_mode` ani `busy_timeout`; działa domyślny `timeout=5.0` biblioteki `sqlite3`.
  - `transaction()` (`:150-164`) polega na niejawnym `BEGIN` przed pierwszym zapisem.
- **Blokada logowania.**
  - Odczyt licznika prób (`backend/app/routers/auth.py:94`) i zapis próby (`:108`) nie mają między sobą `await`. Gwarancja limitu działa więc tylko w jednym procesie.
  - Uvicorn czyta `WEB_CONCURRENCY` jako liczbę workerów, a ani `backend/Dockerfile:44`, ani `Makefile:22` nie podają `--workers`.
- **Argon2id i pamięć.** `PasswordHasher()` (`backend/app/security.py:11`) domyślnie zajmuje 64 MiB na wywołanie i działa w puli wątków AnyIO (40 wątków). Kontener API ma `mem_limit: 1g` w `compose.yaml`.
- **Sesje.** Wylogowanie usuwa tylko bieżącą sesję (`backend/app/sessions.py:88-101`). Nie ma żadnej trasy zarządzania kontami.
- **Ryzyka rezydualne opisane w §13** `docs/faza-3-ops/README.md`:
  - sieć `edge` nie jest `internal`;
  - restart `unless-stopped` nie leczy stanu `unhealthy`;
  - SSH jest domyślnie otwarty dla `0.0.0.0/0` i `::/0` (`deploy/ansible/roles/base/defaults/main.yml`);
  - kopia bazy jest ręczna, a odtwarzanie nie jest opisane (§10, `:262-270`).
- **Rozjazdy dokumentacji.**
  - Repozytorium jest publiczne (`gh repo view`), a `.github/workflows/ci.yml:14` twierdzi, że prywatne.
  - `docs/faza-3-ops/README.md:319` i `:328` piszą, że publikacja w GHCR nie była sprawdzona. Tymczasem przebieg `44694936930` na `main` (job `publish`: `success`) ją wykonał.
- **`.gitignore`.** Wiersz `reports/` (`.gitignore:20`) ignoruje też `docs/testing/reports/`. Nowy raport QA nie trafia więc do commitu bez `git add -f`.
- **Porty.**
  - 8080 zajmuje klaster kind `secure-k8s-aiops-*`, a 8443 i 8081 działający stos compose `patchpoint` użytkownika. `/qa:run` wymaga 8080 i 8443, dlatego testy idą ręcznie.
  - Wolne są porty 18000, 18080, 18443, 18100–18102, 28080, 28443 i 2222.
  - Podsieć `10.250.0.0/24` zajmuje stos użytkownika, a `10.251.0.0/24` smoke.

## Macierz uwag prowadzącego

Identyfikatory uwag są używane w katalogu scenariuszy i w raporcie końcowym.

| ID | Sekcja oceny | Uwaga (skrót) | Scenariusze |
|---|---|---|---|
| R1.1 | 1 | Przejrzysty proces w trzech fazach, dokumentacja | bez testu (dokumentacja procesu) |
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

## Środowisko testowe

Ta sekcja trafia do sekcji `## Setup` planu testów (Task 1). Polecenia przenoszone są dosłownie, a opisy po angielsku.

**Na starcie każdego zadania wykonawczego**, w katalogu głównym repozytorium:

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

**Instancje deweloperskiego API** uruchamiane przez `make run`. To jeden proces uvicorn z `--no-proxy-headers` (`Makefile:22`), bez proxy, z URL `http://127.0.0.1:<port>`.

| Nazwa | Port | Baza | Dodatkowe zmienne |
|---|---|---|---|
| dev | 18100 | `$RUN/dev/patchpoint.db` | `PATCHPOINT_SEED_DEMO_DATA=true`, `PATCHPOINT_DEMO_PASSWORD="$DEMO_PW"` |
| workers | 18101 | `$RUN/workers/patchpoint.db` | `WEB_CONCURRENCY=4` |
| docs | 18102 | `$RUN/docs/patchpoint.db` | `PATCHPOINT_DOCS_ENABLED=true` |

Start (przykład dla `dev`). Zmienne są przypisane prefiksem powłoki, więc hasło nie trafia do argumentów procesu. `$!` jest PGID, bo `setsid` w skrypcie się nie rozwidla.

```bash
mkdir -p "$RUN/dev"
PATCHPOINT_DATABASE_PATH="$RUN/dev/patchpoint.db" PATCHPOINT_SEED_DEMO_DATA=true PATCHPOINT_DEMO_PASSWORD="$DEMO_PW" \
  setsid make run API_PORT=18100 > "$RUN/dev/api.log" 2>&1 &
echo $! > "$RUN/dev/pgid"
for i in $(seq 60); do curl -sf --noproxy '*' -o /dev/null http://127.0.0.1:18100/api/health && break; sleep 1; done
```

Stop: `kill -TERM -- "-$(cat "$RUN/dev/pgid")"`. Kontrola stanu bazy: `sqlite3 -readonly "$RUN/dev/patchpoint.db" "<SQL>"`.

**Stos `patchpoint-final`** działa w trybie lokalnym: bez przekierowania na HTTPS, z HSTS 0 i ciasteczkiem `session`. Obrazy `patchpoint-*:local` pochodzą z OPS-01. Gdy `docker image inspect patchpoint-api:local` się nie powiedzie, zbuduj je jak w OPS-01.

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

Sprzątanie: `docker compose down -v` z tymi samymi zmiennymi.

**Tempo żądań przez proxy.** `/api/auth/login` i `/api/auth/register` dzielą strefę limitu `patchpoint_auth`: 10 na minutę, seria 5 (`deploy/proxy/templates/conf.d/patchpoint-limits.conf.template`, `deploy/proxy/templates/includes/patchpoint-app.conf.template:28-36`).

- Przed każdym żądaniem uwierzytelniania przez proxy: `sleep 7`.
- Wyjątki od tej reguły: FE-06, krok 15 OPS-04 i krawędź a) OPS-05.
- Po scenariuszu z serią żądań odczekaj 65 s.

**Sekrety i dowody.**

- **Gdzie trzymamy sekrety.** Hasła trzymamy tylko w plikach w `$RUN`. Do curla trafiają przez `--data-binary @plik`, do jq przez stdin, nigdy jako argument polecenia. Tokeny trzymamy tylko w słoikach curla w `$RUN`.
- **Zawartość dowodów.** Do dowodów nie trafiają ciała żądań, wartości ciasteczek ani nagłówki `Set-Cookie`.
- **Format bloków.** Każdy blok w pliku dowodów zaczyna się linią `$ <polecenie>` i podaje kod wyjścia. Długie wyjście można skrócić znacznikiem `… [N lines omitted]`, ale linie rozstrzygające wynik zostają.
- **Skan przed zakończeniem zadania.** Najpierw `awk '$6 ~ /session$/ {print $7}' "$RUN"/*.jar >> "$RUN/secrets.txt" 2>/dev/null || true`, potem `grep -rnF -f "$RUN/secrets.txt" "$EVD"` — ma nie zwrócić nic. Na końcu `rm -rf "$RUN"`.
- **Plik wyników zadania** (`results-*.md`, po angielsku) zawiera tabelę `| ID | Kind | Verdict | Evidence | Notes |`. Pod tabelą każdy wynik `Fail` albo `Confirmed` dostaje wpis `**<ID>** — Expected: … — Actual: …` z plikiem i fragmentem dowodu.
- **Sprzątanie.** Zadanie kończy się bez kontenerów `patchpoint-final-*`, `patchpoint-smoke*`, `pp-ansible-target` i `pp-verify-*`, bez wolumenów `patchpoint-final_*` i `pp-ansible-docker` oraz bez procesów nasłuchujących na portach 18100–18102. Kontenery użytkownika zostają nietknięte: projekt `patchpoint`, `secure-k8s-aiops-*` i `vina-searxng`.

## Reguły wyników i napraw

- **Rodzaj `contract`.** `Pass`, gdy spełnione są wszystkie Expected, także w krawędziach. W przeciwnym razie `Fail`.
- **Rodzaj `probe`.** Sprawdza tezę prowadzącego o brakującej zdolności („Remark claim”). Wynik to `Confirmed`, `Not confirmed` albo `Partially confirmed`.
- **`Need info`.** Gdy brakuje narzędzia albo środowiska, wpisz nazwany powód.
- **Zgłoszenia QA-NNN w raporcie końcowym.** Powstają dla każdego `Fail` oraz dla każdej sondy, która przy okazji ujawnia defekt: 5xx, crash lub OOM, utratę gwarancji bezpieczeństwa albo nieprawdziwą dokumentację.
  - Ważność według `qa:report-format`: status ≥ 500 albo crash → CRITICAL; zły status, złe dane albo utracona gwarancja → HIGH; degradacja → MEDIUM; dokumentacja → LOW.
  - Brakujące zdolności z sekcji 3 trafiają tylko do macierzy uwag, bez QA-NNN.
- **Mapa napraw.** Naprawiamy wyłącznie poniższe defekty. Każdy w osobnym zadaniu i tylko wtedy, gdy wskazany scenariusz ma w wynikach bazowych wynik `Fail`. Każdy inny `Fail` dostaje QA-NNN z propozycją naprawy, bez poprawki w tej delivery.

| Defekt | Wyzwalacz | Zadanie |
|---|---|---|
| B1: commit API blokowany przez zewnętrzny odczyt SQLite | BE-05 `Fail` | Task 7 |
| B2: równoległy Argon2 przekracza limit pamięci API | OPS-05 `Fail` | Task 8 |
| B3: liczba workerów uvicorn nie jest przypięta | BE-06 `Fail` | Task 9 |
| B4: defekty ról `base` i `docker` | nieudane kontrole OPS-17 z winy kodu ról | Task 10 |
| B5: rozjazdy dokumentacji i brak opisu odtwarzania | OPS-15 `Fail`; OPS-10 `Pass` | Task 11 |

## Katalog scenariuszy

Katalog jest po angielsku, bo trafia do `docs/testing/plans/` w tej samej formie, co istniejące plany i raporty QA. Każde odwołanie „(plik, symbol)” Task 1 zamienia na `(path:line)` po odczytaniu wiersza w bieżącym drzewie. `$SFX`, `$RUN`, `H`, `S`, `BASE`, `new_user`, `req`, `wave` i `summary` pochodzą z sekcji „Środowisko testowe”.

### FE — Chromium through the stack (`H` = `http://patchpoint.localhost:28080`)

Driven through the OMP `browser` global in `eval` (read `xd://eval/browser` first). One tab: `browser.open(name="pp-final", url=H + "/")`. Use `tab.goto` and actions on visible labels or ids, and `tab.evaluate` for page state. Record the text of `#message` after every action. Wait `sleep 7` before every sign-up or sign-in submit, except in FE-06.

**FE-01 — Sign-up and sign-in through the proxy** · contract · R1.2
- Steps:
  1. In „Rejestracja” fill Login `qa.final.$SFX.owner`, „Imię i nazwisko” `QA Final Owner`, „Dział” `QA` and „Hasło” with the password from `new_user qa.final.$SFX.owner`, then click „Zarejestruj konto”.
  2. Run edges a) and b).
  3. In „Logowanie” fill the same login and password and click „Zaloguj”.
- Expected:
  - After step 1, `#message` reads „Konto utworzone — możesz się zalogować” (frontend/app.js, register handler).
  - After step 3, the app view is shown and the user bar reads „Zalogowano: QA Final Owner (pracownik)” (frontend/app.js, `showAppView`, `ROLE_LABELS`).
  - `document.cookie` contains no `session=` (backend/app/routers/auth.py, `set_cookie` with `httponly=True`).
- Edges:
  - a) The same registration again → „Username is already taken” (auth.py, `USERNAME_TAKEN`).
  - b) Registration of `qa.final.$SFX.owner2` with password `qa.final.$SFX.owner2-Secret-12345` → the message contains „Password must not contain the username” (backend/app/security.py, `password_policy_violation`; exact text — brittle).

**FE-02 — Employee ticket through the UI** · contract · R1.2, R1.3
- Preconditions: signed in as the FE-01 owner.
- Steps:
  1. In „Nowe zgłoszenie”: Tytuł `Drukarka nie drukuje $SFX`, Kategoria „Drukarka”, Priorytet „Wysoki”, Opis `Brak wydruku z kolejki.`; click „Wyślij zgłoszenie”.
  2. Click the row with that title.
  3. In „Nowy komentarz” type `Sprawdziłem kabel.` and click „Dodaj komentarz”.
- Expected:
  - After step 1: „Zgłoszenie wysłane” (app.js, ticket form handler), and the list shows the title with badge „Otwarte”.
  - After step 2: the detail heading is `#<id> Drukarka nie drukuje $SFX`, and there is no `#status-select` or `#assign-button` (app.js, `renderAgentActions`).
  - After step 3: „Komentarz dodany” (app.js, `onCommentSubmit`), and the comment text is shown.
- Edges:
  - a) Tytuł `<script>alert(1)</script>` with the other fields valid → „Request blocked by the proxy” (patchpoint-app.conf.template, `@patchpoint_blocked`). No new row, no dialog, and the form keeps its values (app.js, `ticketForm.reset` only on success).
  - b) „Szukaj” = `$SFX`, then „Filtruj” → exactly one row, the step-1 ticket.

**FE-03 — Agent handles the ticket** · contract · R1.2
- Preconditions:
  1. The FE-02 ticket exists.
  2. Click „Wyloguj” → „Wylogowano” (app.js, logout handler).
  3. Sign in as `helpdesk` with `$DEMO_PW`.
- Steps:
  1. Open the FE-02 ticket.
  2. Click „Przypisz do mnie”.
  3. In `#status-select` choose „W realizacji”, then click „Zmień status”.
  4. Do the same with „Rozwiązane”.
  5. Do the same with „Zamknięte”.
- Expected:
  - The user bar reads „Zalogowano: Piotr Serwisant (agent Helpdesk)” (backend/app/database.py, `DEMO_USERS`; app.js `ROLE_LABELS`).
  - Step 2 shows „Zgłoszenie przypisane do Ciebie” (app.js, `onAssignToMe`).
  - Steps 3–5 each show „Status zmieniony” (app.js, `onStatusChange`), and the final badge is „Zamknięte”.
- Edges:
  - a) Choose „Otwarte” on the closed ticket and click „Zmień status” → „Invalid status transition: closed -> open” (backend/app/routers/tickets.py, `update_ticket`, `ALLOWED_TRANSITIONS`). The badge stays „Zamknięte”.
  - b) The agent's list has at least 4 rows, including the 3 seeded demo tickets (tickets.py, `list_tickets`).

**FE-04 — Session ended outside the UI** · contract · R1.2
- Preconditions: signed in as `helpdesk`.
- Steps:
  1. `tab.evaluate("fetch('/api/auth/logout', {method: 'POST', credentials: 'include'}).then(r => r.status)")` → 200.
  2. Click „Filtruj”.
- Expected: the auth view is shown with „Sesja wygasła lub została zakończona — zaloguj się ponownie.” (app.js, `SESSION_EXPIRED_MESSAGE` and the 401 branch of `api`).
- Edges:
  - a) Reload → the auth view is shown (app.js start-up call to `/api/auth/me` gets 401).
  - b) Sign in as `helpdesk` and click „Wyloguj” → „Wylogowano”. Then `fetch('/api/auth/me')` from the page → 401.

**FE-05 — CSP enforced by the proxy header** · contract · R1.2, R1.3
- Preconditions: `/` is loaded.
- Steps, in one `tab.evaluate`:
  1. Register a `securitypolicyviolation` listener that collects `violatedDirective`.
  2. Append a `<script>` element with text `window.__cspProbe = 1`.
  3. `try { eval('1') } catch (e) { evalError = e.name }`.
  4. `try { await fetch('https://example.com/') } catch (e) { fetchError = e.name }`.
  5. Wait 500 ms and return all values.
- Expected (patchpoint-app.conf.template, `location /` header `script-src 'self'`, `connect-src 'self'`):
  - `window.__cspProbe` is undefined.
  - At least one violated directive starts with `script-src`.
  - `evalError` is `EvalError`.
  - `fetchError` is `TypeError`.
- Edges:
  - a) The `meta[http-equiv="Content-Security-Policy"]` content contains `connect-src 'self'` (deploy/proxy/Dockerfile, `sed` in the `ui` stage).
  - b) `fetch('/', {method: 'HEAD'})` headers: `x-frame-options` = `DENY`, and `content-security-policy` contains `frame-ancestors 'none'`.

**FE-06 — Login rate limit and lockout in the UI (last FE scenario)** · contract · R1.3
- Preconditions: the auth view is shown, and the FE-01 owner exists.
- Steps: submit „Zaloguj” 7 times without pause, with the owner's login and password `Wrong-Password-12345`.
- Expected:
  - Every message is one of:
    - „Invalid username or password” (auth.py, `INVALID_CREDENTIALS`);
    - „Too many failed login attempts. Try again later.” (auth.py, `LOGIN_BLOCKED`);
    - „Too many requests, try again later” (patchpoint-app.conf.template, `@patchpoint_rate_limited`).
  - The 7th message is one of the two 429 texts.
  - The UI never shows „Błąd serwera (HTTP …)” (app.js, `api`).
- Edges:
  - a) Immediately afterwards, the correct password → no app view, and the message is a 429 text.
  - b) Wait 65 s, make 5 more wrong attempts 7 s apart, then submit the correct password → „Too many failed login attempts. Try again later.” (auth.py, lockout check before verification).

### BE — HTTP on the development API (`BASE=http://127.0.0.1:18100`, instance `dev`, unless stated)

**BE-01 — API version in OpenAPI** · contract · R2.5
- Steps (instance `docs`, `BASE=http://127.0.0.1:18102`): `req GET /openapi.json`, then `req GET /docs`.
- Expected:
  - `/openapi.json` returns 200 with `.info.version == "0.3.0"` (backend/app/config.py, `APP_VERSION`; backend/app/main.py, `FastAPI(version=…)`).
  - `/docs` returns 200 with `text/html`.
- Edges:
  - a) On `dev`, `/openapi.json` → 404 (config.py, `docs_enabled` default false).
  - b) `backend/pyproject.toml` has `version = "0.3.0"`.

**BE-02 — Parallel sign-up and sign-in** · contract · R3.8
- Preconditions: `new_user` for `qa.final.$SFX.p01`…`p20`, registered one by one (201 each).
- Steps:
  1. Wave `be02a`, 40 jobs:
     - login of p01…p20, cookie-out `$RUN/p<NN>.jar`;
     - registration of `qa.final.$SFX.n01`…`n20` after `new_user`.
  2. Wave `be02b`, 40 jobs: each p-user sends `POST /api/tickets` twice with its jar. Body file: `{"title":"Load $SFX <job id>","description":"Parallel ticket","category":"other","priority":"low"}`.
- Expected:
  - `be02a`: exactly 20×200 and 20×201, and no status ≥ 500 or `000`.
  - `be02b`: 40×201.
  - `SELECT COUNT(*) FROM users` → 43 (3 demo + 40).
  - `SELECT COUNT(*) FROM tickets` → 43 (3 demo + 40).
  - `$RUN/dev/api.log` has no `"event": "internal_error"` line (main.py, internal error handler).
  - Record p50/p95/max of both waves.
- Anchors: auth.py `register` (hash in the threadpool before the transaction), auth.py `login`, database.py `transaction`.
- Edges:
  - a) A third wave with the same 20 logins and wrong passwords → 20×401, with no status ≥ 500.

**BE-03 — Parallel wrong passwords versus the lockout** · contract · R3.8
- Preconditions: `qa.final.$SFX.lock` is registered.
- Steps: wave of 20 `POST /api/auth/login` for `.lock` with `{"username": …, "password": "Wrong-Password-12345"}`.
- Expected (auth.py, lockout check and `record_login_failure`; config.py `login_max_failures` = 5, `login_lockout_minutes` = 15):
  - exactly 5×401 „Invalid username or password”;
  - 15×429 „Too many failed login attempts. Try again later.”, each with `Retry-After` `900`;
  - `SELECT COUNT(*) FROM login_failures WHERE username = 'qa.final.$SFX.lock'` → 5.
- Edges:
  - a) The correct password afterwards → 429.
  - b) A correct login of `qa.final.$SFX.p01` → 200 (the lockout is per username: sessions.py, `is_login_blocked`).

**BE-04 — Parallel conflicting status changes** · contract · R3.8
- Preconditions:
  - `qa.final.$SFX.emp` is registered and signed in, and creates 10 tickets one by one (201 each).
  - `helpdesk` is signed in (jar).
- Steps: wave of 20 `PATCH /api/tickets/<id>` as the agent: per ticket, one `{"status":"in_progress"}` and one `{"status":"closed"}`.
- Expected (tickets.py, `update_ticket`, `ALLOWED_TRANSITIONS`):
  - Per ticket, exactly one 200 and one 400 whose detail starts with „Invalid status transition:”.
  - `GET /api/tickets/<id>` as the agent shows the status of the request that got 200.
  - No status ≥ 500.
- Edges:
  - a) Agent `PATCH` with `{}` → 400 „Nothing to update”.
  - b) `.emp` `PATCH` → 403 „Helpdesk agent role required” (backend/app/dependencies.py, `require_agent`).

**BE-05 — API write during an external SQLite read transaction** · contract · R3.8
- Preconditions:
  - `qa.final.$SFX.wal` is registered.
  - Record `sqlite3 -readonly "$RUN/dev/patchpoint.db" 'PRAGMA journal_mode'`.
  - Run edge a) first.
- Steps, with `t` in seconds from the start of the reader:
  1. Start a background reader: `python3` with `sqlite3.connect(db, isolation_level=None)`, `BEGIN`, `SELECT COUNT(*) FROM users`, sleep 15, `ROLLBACK`.
  2. At t≈1: `req POST /api/auth/login --data-binary @<wrong-password body for .wal>`.
  3. At t≈1.5–5.5: five `GET /api/health`, 1 s apart, each in the background with `-m 30`.
  4. At t≈7: register `qa.final.$SFX.wal2`.
  5. `wait`.
- Expected:
  - The login returns 401 in < 1.0 s.
  - Every health request returns 200 in < 1.0 s.
  - The registration returns 201 in < 1.0 s.
  - The API log has no `internal_error`.
- Known risk (R3.8): in rollback-journal mode the commit waits the busy timeout on the event-loop thread, then fails with 500 `{"detail":"Internal server error","error_id":…}`, and every request stalls. Copy the `internal_error` lines (`exception`, `sql`) from the API log.
- Edges:
  - a) Control without the reader: the login returns 401 in < 1.0 s.

**BE-06 — Several processes (`WEB_CONCURRENCY=4`) versus the lockout** · contract · R3.8
- Preconditions:
  - Instance `workers` started with `WEB_CONCURRENCY=4` in the shell prefix, `BASE=http://127.0.0.1:18101`.
  - `qa.final.$SFX.mp` is registered.
- Steps:
  1. Count the `Started server process` lines in `$RUN/workers/api.log`.
  2. Wave of 20 wrong logins for `.mp`.
  3. `SELECT COUNT(*) FROM login_failures WHERE username = 'qa.final.$SFX.mp'` on the `workers` database.
  4. Wave of 40 registrations `qa.final.$SFX.w01`…`w40`.
- Expected:
  - Exactly 1 server process.
  - 5×401 and 15×429.
  - The count is 5.
  - 40×201, with no status ≥ 500 or `000`.
- Known risk: uvicorn reads `WEB_CONCURRENCY` as its worker count, and the per-process event loops interleave the count read and the failure write (auth.py `login`).
- Edges:
  - a) Control: the same 20-guess wave on `dev` gives 5×401.

**BE-07 — No account-management API** · probe · R3.9, R1.2
- Remark claim: there is no way to create an agent, to change or reset a password, or to revoke all sessions of a user.
- Steps, as the agent (`helpdesk` jar):
  - `GET /api/users`
  - `POST /api/users` `{}`
  - `PATCH /api/users/1` `{"role":"agent"}`
  - `DELETE /api/users/2`
  - `POST /api/auth/password` `{}`
  - `POST /api/auth/password-reset` `{}`
  - `POST /api/auth/logout-all`
  - `DELETE /api/auth/sessions`
- Expected: each returns 404 `{"detail":"Not Found"}`, because only the routers `health`, `auth` and `tickets` are included (main.py, `include_router`). If so → `Confirmed`.
- Edges:
  - a) `POST /api/auth/register` with a valid body for `qa.final.$SFX.escalate` plus `"role": "agent"` → 422. `SELECT COUNT(*) FROM users WHERE username = 'qa.final.$SFX.escalate'` → 0 (backend/app/schemas.py, `UserCreate` with `extra="forbid"`).
  - b) `SELECT username FROM users WHERE role = 'agent'` → only `helpdesk`.

**BE-08 — Logout ends only the current session** · probe · R3.9
- Remark claim: after an account takeover, the other sessions of the user cannot be revoked.
- Preconditions: `qa.final.$SFX.multi` is registered and signed in twice, with jars A and B.
- Steps:
  1. `SELECT COUNT(*) FROM sessions s JOIN users u ON u.id = s.user_id WHERE u.username = 'qa.final.$SFX.multi'`.
  2. `POST /api/auth/logout` with A.
  3. `GET /api/auth/me` with A, then with B.
  4. Repeat the count.
- Expected (sessions.py, `end_session`):
  - The first count is 2.
  - The logout returns 200 `{"message":"Logged out"}`.
  - me(A) returns 401 „Not authenticated”.
  - me(B) returns 200.
  - The second count is 1.
  - If so → `Confirmed`.
- Edges:
  - a) `POST /api/auth/logout` without a cookie → 200 `{"message":"Logged out"}` (auth.py, `logout`).

### OPS — containers, host and repository

**OPS-01 — Baseline gates** · contract · R1.2, R1.3, R1.4, R2.7
- Steps: run the following in order, recording each with `$ <command>` and its exit code.
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
- Expected:
  - Every exit code is 0.
  - pytest reports `145 passed` with `TOTAL` ≥ 80%.
  - Semgrep reports 0 findings and `.errors | length` = 0 (scripts/scan.sh, semgrep gate).
  - The smoke run ends with `STACK SMOKE ZAKOŃCZONY POWODZENIEM`, with 28 `[OK]`, 0 `[BŁĄD]` and `22 × [NAPRAWIONE]` (scripts/stack_smoke.sh).

**OPS-02 — Container hardening of the running stack** · contract · R1.3
- Steps:
  - `docker inspect` of `patchpoint-final-api-1` and `patchpoint-final-proxy-1`;
  - `docker compose exec -T proxy id -u`;
  - `docker network inspect patchpoint-final_backend -f '{{.Internal}}'`;
  - `docker compose port api 8000`.
- Expected (compose.yaml, services and networks):
  - **api:**
    - `Config.User` `10001:10001`, `ReadonlyRootfs` true, `CapDrop` `["ALL"]`, `SecurityOpt` `["no-new-privileges:true"]`;
    - `Memory` 1073741824, `NanoCpus` 1000000000, `PidsLimit` 256;
    - `LogConfig` json-file with `max-size` 10m and `max-file` 5;
    - only network `patchpoint-final_backend`, and no published port (empty or `:0`).
  - **proxy:**
    - `Config.User` `nginx` with uid 101, `ReadonlyRootfs` false (docs/faza-3-ops/README.md §13), `CapDrop` `["ALL"]`, `no-new-privileges:true`;
    - `Memory` 268435456, `NanoCpus` 500000000, `PidsLimit` 128;
    - the same logging;
    - networks `patchpoint-final_edge` and `patchpoint-final_backend`, and ports `127.0.0.1:28080` and `127.0.0.1:28443`.
  - The `backend` network has `Internal` true.

**OPS-03 — TLS protocols and ciphers** · contract · R1.3
- Steps: `openssl s_client -connect 127.0.0.1:28443 -servername patchpoint.localhost -CAfile deploy/proxy/dev-tls/fullchain.pem </dev/null`, once with each option set below.
  - `-tls1_3`
  - `-tls1_2 -cipher ECDHE-ECDSA-AES128-GCM-SHA256`
  - `-tls1_2 -cipher ECDHE-ECDSA-AES128-SHA`
  - `-tls1_1 -cipher 'DEFAULT:@SECLEVEL=0'`
  - Then, separately: `curl -s --noproxy '*' -o /dev/null "$S/api/health"` without `--cacert`.
- Expected (docs/faza-3-ops/README.md §6, TLS bullet):
  - The first two complete the handshake: protocol TLSv1.3 and TLSv1.2, `Verify return code: 0 (ok)`.
  - The third and fourth fail with a non-zero exit.
  - curl exits with 60.

**OPS-04 — Security events in the logs** · contract · R1.2, R3.10
- Preconditions:
  - 65 s have passed since FE-06.
  - `new_user` has run for `qa.final.$SFX.log1` and `.log2`.
  - All requests use `BASE=$H`.
- Steps:
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
- Expected statuses, step by step:
  - 1: 201
  - 2: 409
  - 3: 401×5
  - 4: 429
  - 5: 401
  - 6: 201, 200
  - 7: 401
  - 8: 404
  - 9: 403
  - 10: 201, 200, 200
  - 11: 422
  - 12: 200
  - 13: 403 „Origin not allowed”
  - 14: 403 and 403 „Request blocked by the proxy”
  - 15: at least one 429 „Too many requests, try again later”
- Expected API log: one JSON line per event (backend/app/audit.py, `log_security_event`). Every `client_ip` is the same address, and it is not `10.253.0.10` (compose.yaml, `FORWARDED_ALLOW_IPS`). The events:
  - `user_registered` with role `employee`
  - `registration_conflict`
  - `login_failed` with reason `bad_password`, 5 times
  - `login_blocked`
  - `login_failed` with reason `unknown_user`
  - `login_succeeded`
  - `session_rejected` with reason `unknown`
  - `access_denied` with reason `not_ticket_owner` and ticket id 1
  - `access_denied` with reason `agent_role_required`
  - `ticket_updated`
  - `validation_failed`, with field names and types only
  - `logout`
- Expected proxy log:
  - ModSecurity audit JSON with `ruleId` 942… and 941…;
  - an nginx `limiting requests` warning.
- Expected hygiene: `grep -F -f "$RUN/secrets.txt"` over both logs returns nothing.
- Observation for R3.10 (no verdict of its own):
  - Whether step 13 left any log line. `OriginCheckMiddleware` in backend/app/middleware.py logs nothing.
  - compose.yaml has no log shipper, so the logs stay local (docs/faza-3-ops/README.md §10).

**OPS-05 — Parallel logins versus the API memory limit** · contract · R3.8
- Preconditions: a fresh stack, and `RC0=$(docker inspect -f '{{.RestartCount}}' patchpoint-final-api-1)`.
- Steps:
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
- Expected:
  - 40×201 for the registrations.
  - 40×200 for the logins, with no `000` and no status ≥ 500.
  - `false <RC0> running`.
  - The highest sampled memory is < 1GiB (compose.yaml, `mem_limit: 1g`).
- Known risk: `PasswordHasher()` defaults use 64 MiB per hash (security.py), and up to 40 hashes run at once in the threadpool.
- Edges:
  - a) Through the proxy from one IP: 12 parallel wrong logins return only 401 or 429, with no 502 or 504 (patchpoint-app.conf.template, `limit_req` on login).

**OPS-06 — API restart after the process exits** · contract · R1.3
- Preconditions:
  - `helpdesk` is signed in through `H` (jar).
  - `N0` = the number of tickets in `GET /api/tickets?limit=100`.
  - The `RestartCount` of api and of proxy are recorded.
- Steps:
  1. `docker compose exec -T api python -c "import os, signal; os.kill(1, signal.SIGTERM)"`.
  2. Every 1 s for 90 s, run `curl -s --noproxy '*' -m 10 -o /dev/null -w '%{http_code} %{time_total}\n' "$H/api/health"`.
- Expected (compose.yaml `restart: unless-stopped` and volume `api-data`; patchpoint-proxy.conf.template, variable `proxy_pass`):
  - 200 again within 60 s.
  - During the outage only 502 or 504, and no request takes longer than 10 s.
  - The api `RestartCount` is +1, and the proxy count is unchanged.
  - After a new agent login, the ticket count equals `N0`.

**OPS-07 — Hung proxy** · probe · R3.5
- Remark claim: an unhealthy proxy is not restarted automatically (docs/faza-3-ops/README.md §13, nginx bullet).
- Steps:
  1. `docker compose exec -T proxy sh -c 'pkill -STOP -f "nginx: worker process"'`. If `pkill` is missing: `for p in $(ps -o pid,args | awk '/nginx: worker process/ && !/awk/ {print $1}'); do kill -STOP "$p"; done`.
  2. Confirm the workers are in state `T` with `ps -o pid,stat,args`.
  3. Every 10 s for 180 s, record:
     - `docker inspect -f '{{.State.Health.Status}} {{.RestartCount}} {{.State.Status}}' patchpoint-final-proxy-1`;
     - `curl -s --noproxy '*' -m 5 -o /dev/null -w '%{http_code}' "$H/api/health"; echo " exit=$?"`.
  4. `docker compose restart proxy`, then poll `/api/health` for up to 60 s.
- `Confirmed` if:
  - the health status reaches `unhealthy`;
  - `RestartCount` does not change and `Status` stays `running`;
  - curl exits with 28 until the manual restart;
  - after the restart, `/api/health` returns 200 within 60 s.

**OPS-08 — Container egress** · probe and contract · R3.6, R1.3
- Remark claim: the proxy has unrestricted Internet egress (docs/faza-3-ops/README.md §13, egress bullet).
- Steps:
  1. Host control: `curl -s --noproxy '*' -m 10 -o /dev/null -w '%{http_code}' https://www.google.com/generate_204`.
  2. `docker compose exec -T proxy curl -s -m 10 -o /dev/null -w '%{http_code}' https://www.google.com/generate_204`.
  3. `docker compose exec -T api python -c "import socket; socket.create_connection(('1.1.1.1', 443), timeout=5)"`, recording the exit code.
- Results:
  - `Confirmed` if the proxy gets 204.
  - Contract: the API connection fails (compose.yaml, the `backend` network is `internal`).
  - `Need info` if the host control fails.

**OPS-09 — SQLite backup per §10** · contract · R3.7
- Preconditions: the OPS-05 data, plus a ticket with one comment by `.m01` created through `H`.
- Steps:
  1. Run the three commands of docs/faza-3-ops/README.md §10 (`:265-267`), with `--project-directory /opt/patchpoint` replaced by the stack environment above, and copy the file to `$RUN/backup/patchpoint.db`.
  2. `sqlite3 "$RUN/backup/patchpoint.db" 'PRAGMA integrity_check'`.
  3. Count `users`, `tickets` and `comments` in the backup (`sqlite3 -readonly`) and in the live database (`docker compose exec -T api python -c` with `sqlite3.connect('file:/data/patchpoint.db?mode=ro', uri=True)`).
- Expected:
  - All three commands exit with 0.
  - The integrity check prints `ok`.
  - The counts are equal.
  - `/data/backup.db` no longer exists afterwards.

**OPS-10 — Restore drill and data persistence** · contract · R3.7
- Steps:
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
- Expected:
  - a) The counts are unchanged, and the `.m01` login returns 200.
  - b) The stack is healthy and the counts equal the backup counts. `.m01` searching for `restore-marker-$SFX` finds nothing, and the `.m02` login returns 200.

**OPS-11 — Secrets in the git history** · probe and contract · R3.3
- Remark claim: secrets are scanned only in the current tree, and nothing scans the history (scripts/scan.sh, `fs` with `--scanners vuln,secret,misconfig`; `.git` is skipped).
- Steps:
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
- Results:
  - Contract: the `git log` output is empty.
  - `Confirmed` if the grep is empty.
  - Every gitleaks finding is triaged with its rule, file, short commit and classification: `true positive` or `false positive: <reason>`. A true positive is a HIGH QA issue: rotate the secret, do not rewrite the history.
  - Copy the redacted report to `$EVD/gitleaks.json`.

**OPS-12 — IaC scan of compose, Dockerfiles, Ansible and workflows** · probe · R3.4
- Remark claim: compose.yaml and Ansible are not covered by an IaC scanner. Trivy `misconfig` covers the Dockerfiles only (docs/faza-3-ops/dowody/README.md, trivy-fs row).
- Steps:
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
- Results:
  - `Confirmed` if the grep is empty.
  - Every HIGH and MEDIUM finding is classified as `documented (§ ref)`, `false positive: <reason>` or `new defect`. A `new defect` becomes a QA issue and is not fixed here.

**OPS-13 — Semgrep without network** · probe · R3.2
- Remark claim: the rule packs are fetched from the registry at scan time.
- Steps: the arguments of scripts/scan.sh (semgrep branch) plus `--network none`:
  ```bash
  mkdir -p "$RUN/sg"
  docker run --rm --network none --user "$(id -u):$(id -g)" -e HOME=/tmp -e SEMGREP_SEND_METRICS=off \
    -v "$PWD:/src:ro" -v "$RUN/sg:/reports" -w /src \
    semgrep/semgrep:1.185.0@sha256:67518c174185a2043fdbed16c70631b79209499b3671178e7194379b48295a0d \
    semgrep scan --metrics=off --error --config p/python --config p/javascript --config p/dockerfile \
    --config p/docker-compose --config p/github-actions --config p/owasp-top-ten --json-output=/reports/semgrep.json .
  ```
  Record the exit code and the error lines.
- `Confirmed` if the exit code is not 0 and the output names a failed configuration download.

**OPS-14 — Supply chain, static checks** · contract and probe · R1.4, R3.1, R3.3
- Contract checks:
  - Every `^FROM` line in backend/Dockerfile and deploy/proxy/Dockerfile contains `@sha256:`.
  - Every `*_IMAGE="…"` line in scripts/scan.sh contains `@sha256:`.
  - Every `uses:` in .github/workflows/ci.yml ends with `@<40 hex> # v…`.
  - `.trivyignore` has no line that is neither a comment nor blank.
- Probes:
  - `grep -nE '^\s*schedule:' .github/workflows/ci.yml` is empty → R3.3, scheduled scans: `Confirmed`.
  - `grep -niE 'sbom|syft|cosign|attest' .github/workflows/ci.yml` is empty → R3.1: `Confirmed`.
  - An anonymous token request to `https://ghcr.io/token?scope=repository:l3x1cn/patchpoint/api:pull` returns no token; record it, since the packages are private.
  - The two `digest: sha256:…` lines of `gh run view 44694936930 --job <publish job id> --log` are recorded.

**OPS-15 — Documentation consistency** · contract · R2.4, R2.6
- Checks:
  - `gh repo view --json visibility` agrees with the comment at `.github/workflows/ci.yml:13-15`.
  - docs/faza-3-ops/README.md `:319` and `:328` agree with run 44694936930. The publish job's conclusion comes from `gh run view 44694936930 --json jobs`.
  - `git ls-files` lists `docs/testing/plans/2026-11-27-patchpoint-phase-3-ops-test-plan.md` and `docs/testing/reports/2026-11-27-patchpoint-phase-3-ops-report.md`.
  - `docs/faza-3-ops/dowody/ci.md` mentions 44694936930.
  - `git check-ignore -q docs/testing/reports/x.md` exits with 1 (Task 1).
- Expected: everything agrees.
- Predicted: the first two checks disagree → `Fail` (LOW) → fix B5.

**OPS-16 — Ansible, static checks** · contract and probe · R2.1, R3.7
- Steps, from `deploy/ansible`:
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
  4. Run the `argv` of the task „Utwórz tymczasowy certyfikat TLS do pierwszego startu proxy” (roles/patchpoint/tasks/main.yml) for `helpdesk.example.com`, writing into `$RUN/tls/`, and inspect it with `openssl x509 -noout -ext subjectAltName,basicConstraints,extendedKeyUsage`.
  5. `grep -rniE 'fail2ban|sshguard|crowdsec' deploy/ README.md docs/faza-3-ops/README.md`.
- Contract:
  - Both renders and both `nft -c` runs exit with 0.
  - `example.conf` contains `ip saddr { 198.51.100.0/24 } tcp dport 22 accept` and no `ip6 saddr`.
  - The certificate has `DNS:helpdesk.example.com`, a `critical` `CA:FALSE` and `TLS Web Server Authentication` (R2.1).
- Probes (R3.7):
  - `defaults.conf` contains `ip saddr { 0.0.0.0/0 } tcp dport 22 accept` and `ip6 saddr { ::/0 } tcp dport 22 accept` → „SSH open to the Internet by default”: `Confirmed`, documented in §4.
  - The grep is empty → „no fail2ban/sshguard”: `Confirmed`.

**OPS-17 — Ansible roles `base` and `docker` on a systemd container** · contract · R2.2, R2.3, R3.7
- Preconditions, in `$RUN/at/`:
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
  6. The collections are already installed by `make ansible-lint`.
- Steps:
  - a) First run, from `deploy/ansible`:
    ```bash
    ANSIBLE_ROLES_PATH=roles ANSIBLE_COLLECTIONS_PATH=.ansible/collections \
      uv run --locked --python 3.13 --project tools ansible-playbook -i "$RUN/at/inventory.yml" "$RUN/at/site-test.yml"
    ```
  - b)–i) The checks below, run with `docker exec pp-ansible-target …`.
  - j) A second run of the same playbook.
  - Teardown: `docker rm -f pp-ansible-target`, `docker volume rm pp-ansible-docker`, `docker rmi pp-ansible-target:test`.
- Expected:
  - a) The recap shows `failed=0` and `unreachable=0`.
  - b) In the output of run 1, `RUNNING HANDLER [base : Przeładuj konfigurację systemd]` comes before `RUNNING HANDLER [base : Przeładuj nftables]` (roles/base/handlers/main.yml).
  - c) `systemctl show nftables -p DropInPaths -p ExecStop` lists `/etc/systemd/system/nftables.service.d/10-patchpoint.conf`, and `nft delete table inet patchpoint_host` with `ignore_errors=yes` (roles/base/tasks/main.yml, drop-in task).
  - d) `systemctl is-active nftables ssh docker` prints `active` three times. `nft list table inet patchpoint_host` shows `policy drop` and `tcp dport 22 accept`.
  - e) `N1=$(nft list ruleset | grep -c 'chain DOCKER')` is greater than 0. After `systemctl restart nftables`, the same count equals `N1`.
  - f) `nft delete table inet patchpoint_host; systemctl stop nftables` exits with 0, and `systemctl show -p Result nftables` prints `Result=success`. `systemctl start nftables` restores the table.
  - g) `sshd -T` contains `permitrootlogin no`, `passwordauthentication no`, `kbdinteractiveauthentication no`, `x11forwarding no`, `allowtcpforwarding no` and `maxauthtries 3` (roles/base/templates/sshd-patchpoint.conf.j2).
  - h) Start `docker exec -d pp-ansible-target python3 -m http.server 8081`. Read the target IP with `docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' pp-ansible-target`. Then `docker run --rm alpine:3.24 sh -c 'nc -z -w 3 <ip> 8081; echo "8081:$?"; nc -z -w 3 <ip> 22; echo "22:$?"'` prints `8081:1` and `22:0`. If BusyBox `nc` rejects `-z`, run `apk add --no-cache netcat-openbsd` first.
  - i) `/etc/apt/apt.conf.d/20auto-upgrades` contains `APT::Periodic::Update-Package-Lists "1";` and `APT::Periodic::Unattended-Upgrade "1";`. `apt-config dump` contains `origin=Docker,label=Docker CE`.
  - j) The recap of run 2 shows `changed=0` and `failed=0`.
- `Need info` (named reason) if:
  - the target never reaches `running` or `degraded` within 120 s; or
  - `journalctl -u docker` in the target shows a storage or cgroup error that is unrelated to the roles.

**OPS-18 — CI on GitHub** · contract · R1.4, R2.6, R2.7
- Steps (Task 13):
  1. Push the delivery branch and open a draft PR to `main`.
  2. Wait for the `CI` workflow run for the pushed head SHA, with event `pull_request`.
- Expected (.github/workflows/ci.yml, jobs):
  - The run concludes with `success`.
  - `quality`, `semgrep`, `trivy-fs`, `ansible`, `scripts` and `build` are `success`.
  - `publish` is `skipped`.

## Approach

Zadania 2–6 wykonują testy i zapisują dowody. Nie zmieniają żadnego pliku spoza swoich list: wynik `Fail` jest zapisywany, a nie naprawiany. Zadania 7–11 naprawiają wyłącznie defekty z mapy napraw, każde tylko przy swoim wyzwalaczu. Zadanie 12 testuje ponownie po poprawkach, zadanie 13 uruchamia CI, a zadanie 14 składa raport. Kolejność jest obowiązkowa, bo każde zadanie korzysta z wyników poprzednich.

### Task 1: Plan testów końcowych i śledzenie raportów QA
**Commit:** docs: add the final test plan and stop ignoring QA reports

**Files:**
- Create: `docs/testing/plans/2026-11-27-patchpoint-final-test-plan.md`
- Modify: `.gitignore`

1. **`.gitignore`.** Zastąp wiersz 20 `reports/` wierszem `/reports/`. Katalog wyników skanerów leży w korzeniu repozytorium: `scripts/scan.sh` wykonuje `cd` do korzenia i ustawia `REPORTS="$PWD/reports"`. Dotychczasowy wzorzec ignoruje też `docs/testing/reports/`. Sprawdź:
   - `git check-ignore -v reports/x.json` → dopasowanie `/reports/`;
   - `git check-ignore -q docs/testing/reports/x.md` → kod 1.
2. **Plan testów.** Utwórz plik po angielsku, w strukturze `qa:test-plan-format` (przeczytaj `skill://qa:test-plan-format`). Sekcje w tej kolejności:
   1. `# Test Plan: PatchPoint final tests — whole application and the instructor's review`.
   2. `## Setup` — sekcja „Środowisko testowe” z pliku planu delivery (ścieżka planu jest w poleceniu zadania). Bloki kodu, tabele i polecenia przenieś dosłownie, opisy przetłumacz.
   3. `## Source`:
      - Type: `whole application on branch <git branch --show-current>`;
      - Base: `3444344` (root commit `init`);
      - Date: dzisiejsza;
      - Branch: bieżąca gałąź;
      - Head: `git rev-parse HEAD`.
   4. `## Changes Summary`:
      - zakres: backend, frontend, proxy z WAF, compose, Ansible, CI;
      - tabela uwag R1.1–R3.10 z sekcji „Macierz uwag prowadzącego”, z polską kolumną „Uwaga” bez zmian;
      - jedno zdanie, że testy wykonuje się ręcznie, bo porty 8080 i 8443 wymagane przez `/qa:run` są zajęte.
   5. `## Blockers / Findings` — `None found.`
   6. `## Users`:
      - `- owner: registered — qa.final.$SFX.owner (FE)`;
      - `- agent: existing — seeded demo agent helpdesk, password = the run's PATCHPOINT_DEMO_PASSWORD`;
      - `- employees: registered — qa.final.$SFX.<role> per scenario (BE, OPS)`.
   7. `## Detected Tools`:
      - Chromium through the OMP `browser` (sprawdzane w Task 3);
      - curl, jq, sqlite3, openssl, docker 29.10.0, docker compose 5.8.0, gh, uv 0.13.8;
      - gitleaks, KICS i curl w kontenerach o przypiętych digestach;
      - brak hey, wrk i ab.
   8. `## Verdict rules` — sekcja „Reguły wyników i napraw” po angielsku, z tabelą mapy napraw.
   9. `## FE Test Scenarios`, `## BE Test Scenarios` i `## OPS Test Scenarios`. Każdy scenariusz z „Katalogu scenariuszy” jako `### <ID>: <title>`, z polami Kind, Remarks, Target, Preconditions, Steps, Expected, Edge cases, a dla sond także „Remark claim”. Treść przenieś dosłownie. Każde odwołanie „(plik, symbol)” zamień na `(path:line)` po odczytaniu tego wiersza w drzewie; główne Expected i każda krawędź mają osobny cytat.
   10. `## Out of harness scope`:
       - VPS: wystawienie certyfikatu Let's Encrypt (rola `letsencrypt`);
       - logowanie do GHCR i wdrożenie po digeście (rola `patchpoint`);
       - DAST i testy obciążeniowe poza sondami OPS-05 i BE-02.
3. **Akceptacja:**
   - każdy identyfikator FE-01–FE-06, BE-01–BE-08 i OPS-01–OPS-18 występuje dokładnie raz jako nagłówek `### `;
   - nie zostało żadne odwołanie bez numeru wiersza;
   - plik nie zawiera żadnej wartości hasła ani tokenu.

### Task 2: Bramki bazowe i testy deweloperskiego API
**Commit:** docs: record baseline gates and dev API results of the final tests

**Files:**
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/ops-01-gates.txt`
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/be-dev-api.txt`
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/results-baseline-dev-api.md`

Wykonaj scenariusze z `docs/testing/plans/2026-11-27-patchpoint-final-test-plan.md` dokładnie według ich kroków i sekcji Setup.

1. Przygotowanie z sekcji Setup: `EVD`, `RUN`, `SFX`, `DEMO_PW` i funkcje.
2. OPS-01, z wyjściem w `ops-01-gates.txt`. Obrazy `patchpoint-*:local` zostają dla zadań 3–4.
3. Uruchom instancje `dev`, `docs` i `workers`. Wykonaj BE-01–BE-08 w kolejności planu, z wyjściem i kontrolami stanu bazy w `be-dev-api.txt`. Instancji `workers` używa tylko BE-06.
4. `results-baseline-dev-api.md`: wiersze OPS-01 i BE-01–BE-08 według reguł z sekcji Verdict rules, a pod tabelą wpisy Expected/Actual dla `Fail` i `Confirmed`.
5. Zatrzymaj instancje, wykonaj skan sekretów, usuń `$RUN` i sprawdź porty 18100–18102.

### Task 3: Przeglądarka i stos w normalnej pracy
**Commit:** docs: record browser and stack results of the final tests

**Files:**
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/fe-stack.md`
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/ops-stack.txt`
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/results-stack.md`

1. Przygotowanie z sekcji Setup planu testów i uruchomienie stosu `patchpoint-final`.
2. FE-01–FE-06 w tej kolejności, przez globalny obiekt `browser` w `eval` (najpierw przeczytaj `xd://eval/browser`). `fe-stack.md` zapisuje, dla każdego kroku i krawędzi, wykonaną akcję i odczytany stan: tekst `#message`, tekst paska użytkownika, wiersze listy i wynik `tab.evaluate`. Bez zrzutów ekranu. Gdy `browser.open` zgłasza wyjątek, FE-01–FE-06 dostają `Need info: tool: browser` i zadanie idzie dalej.
3. OPS-02 i OPS-03, a po 65 s od FE-06 — OPS-04. Wyjście trafia do `ops-stack.txt`.
4. `results-stack.md` z wierszami FE-01–FE-06 i OPS-02–OPS-04.
5. `docker compose down -v`, skan sekretów, usunięcie `$RUN`.

### Task 4: Obciążenie, awarie i kopie zapasowe na stosie
**Commit:** docs: record load, failure and backup results of the final tests

**Files:**
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/ops-resilience-data.txt`
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/results-resilience-data.md`

1. Przygotowanie z sekcji Setup i świeży stos `patchpoint-final` (nowy wolumen).
2. OPS-05, OPS-06, OPS-07, OPS-08, OPS-09 i OPS-10 w tej kolejności. Liczniki `RestartCount` odczytuj bezpośrednio przed każdym scenariuszem, bo OPS-05 może zrestartować API.
3. `results-resilience-data.md` z wierszami OPS-05–OPS-10. W OPS-10 zapisz dokładne polecenia procedury odtwarzania, które zadziałały. Task 11 przenosi je do dokumentacji.
4. `docker compose down -v`, skan sekretów, usunięcie `$RUN`.

### Task 5: Repozytorium, łańcuch dostaw i Ansible statycznie
**Commit:** docs: record repository, supply chain and static Ansible results

**Files:**
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/ops-repo.txt`
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/gitleaks.json`
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/kics-summary.txt`
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/results-repo.md`

1. Przygotowanie z sekcji Setup planu testów.
2. OPS-11–OPS-16 w tej kolejności, z wyjściem w `ops-repo.txt`.
   - Do `gitleaks.json` trafia zredagowany raport gitleaks, albo `[]` przy braku znalezisk.
   - `kics-summary.txt` zawiera liczniki ważności oraz zapytania HIGH i MEDIUM z plikami i wierszami. Pełny raport KICS zostaje w `$RUN`.
3. `results-repo.md` z wierszami OPS-11–OPS-16 oraz klasyfikacją każdego znaleziska gitleaks i KICS, zgodnie z OPS-11 i OPS-12.
4. Gdy gitleaks znajdzie prawdziwy sekret, pierwszą linią `results-repo.md` jest `TRUE POSITIVE SECRET IN HISTORY — rotate`. Historia nie jest przepisywana.
5. Skan sekretów i usunięcie `$RUN`.

### Task 6: Ansible na kontenerze systemd
**Commit:** docs: record the Ansible container test results

**Files:**
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/ops-17-ansible.txt`
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/results-ansible.md`

1. OPS-17 dokładnie według planu testów. Do `ops-17-ansible.txt` trafiają:
   - pełne wyjście obu przebiegów playbooka;
   - każda kontrola b)–i) z poleceniem i wynikiem.
2. `results-ansible.md`:
   - wiersz OPS-17;
   - lista kontroli a)–j) z `Pass`/`Fail`;
   - dla każdego `Fail`: nazwa zadania Ansible z wyjścia oraz rozstrzygnięcie, czy winny jest kod ról (`role defect`), czy środowisko kontenera (`environment`), z linią dowodu.
3. Sprzątanie celu (polecenia w OPS-17) i usunięcie `$RUN`.

### Task 7: SQLite w trybie WAL (B1)
**Commit:** fix(backend): enable SQLite WAL so external readers do not block API writes

**Files:**
- Modify: `backend/app/database.py`
- Test: `backend/tests/test_database.py`

Warunek: odczytaj BE-05 w `docs/testing/evidence/2026-11-27-patchpoint-final/results-baseline-dev-api.md`. Jeśli wynik nie jest `Fail`, nie zmieniaj niczego i zakończ raportem `**Status:** ✅ Complete — not needed: BE-05 <wynik>`.

1. **Najpierw testy** w `backend/tests/test_database.py`, w konwencji `backend/tests/test_auth.py`: fixture `client`, `settings`, `user_factory`, ścieżki `/api/...` względem `API_BASE_URL` z `tests/support.py`.
   - `test_database_uses_wal_journal_mode` — po starcie aplikacji (fixture `client`) `PRAGMA journal_mode` na `settings.database_path` zwraca `wal`.
   - `test_login_is_not_blocked_by_an_external_read_transaction`:
     1. `user_factory("alice")`;
     2. osobne połączenie `sqlite3.connect(settings.database_path, isolation_level=None)`, na nim `BEGIN` i `SELECT COUNT(*) FROM users` (zbierz wynik);
     3. `POST /api/auth/login` z `{"username": "alice", "password": "wrong-password"}` → status 401;
     4. w `finally`: `ROLLBACK` i zamknięcie połączenia.
   - Uruchom `make test`. Oba testy mają zawieść: tryb `delete`, a logowanie dostaje 500 po około 5 s.
2. **`backend/app/database.py`:**
   - stała `SQLITE_BUSY_TIMEOUT_SECONDS: Final = 5.0`;
   - w `connect()` wywołanie `sqlite3.connect(database_path, timeout=SQLITE_BUSY_TIMEOUT_SECONDS, check_same_thread=False)`. Wartość ta sama co domyślna biblioteki, teraz jawna.
   - w `init_db()` po `_check_schema_version(conn, database_path)`, a przed `conn.executescript(...)`: `fetch_one(conn, "PRAGMA journal_mode = WAL")`. Tryb WAL zapisuje się w pliku bazy, więc dotyczy też baz istniejących.
   - nad tym wywołaniem komentarz: SQLite działa w wątku pętli zdarzeń, więc zablokowany commit wstrzymałby wszystkie żądania. W trybie WAL odczyty spoza API (kopie, powłoka `sqlite3`, kontrole QA) nie blokują jego zapisów.
3. `make test`, `make lint` i `make typecheck` przechodzą.

### Task 8: Ograniczenie równoległego Argon2 (B2)
**Commit:** fix(backend): bound concurrent Argon2 hashing below the API memory limit

**Files:**
- Modify: `backend/app/security.py`
- Test: `backend/tests/test_auth_concurrency.py`

Warunek: OPS-05 w `docs/testing/evidence/2026-11-27-patchpoint-final/results-resilience-data.md` ma wynik `Fail`. W przeciwnym razie nie zmieniaj niczego i zakończ raportem `**Status:** ✅ Complete — not needed: OPS-05 <wynik>`.

1. **Najpierw test** `test_password_hashing_concurrency_is_bounded(monkeypatch)`:
   1. `monkeypatch.setattr(security, "_password_hasher", fake)`. Obiekt `fake` ma metody `hash(password)` i `verify(stored_hash, password)`. Każda pod `threading.Lock` zwiększa licznik bieżących wywołań i zapisuje maksimum, śpi 0,05 s, zmniejsza licznik i zwraca `"$argon2id$fake"` albo `True`.
   2. 12 wątków (`concurrent.futures.ThreadPoolExecutor(max_workers=12)`) woła 6 razy `security.hash_password` i 6 razy `security.verify_password`.
   3. Asercja: `2 <= max_seen <= security.PASSWORD_HASH_CONCURRENCY`.
   4. Przed zmianą test zawodzi: atrybutu nie ma, a maksimum wynosi 12.
2. **`backend/app/security.py`:**
   - `import threading`;
   - `PASSWORD_HASH_CONCURRENCY: Final = 4` z komentarzem: domyślny `PasswordHasher()` argon2-cffi zajmuje 64 MiB na wywołanie, a 4 równoległe wywołania to 256 MiB, poniżej `mem_limit: 1g` API w `compose.yaml`; kolejne żądania czekają w swoim wątku roboczym, nie w pętli zdarzeń;
   - `_hash_slots: Final = threading.BoundedSemaphore(PASSWORD_HASH_CONCURRENCY)`;
   - ciała `hash_password` i `verify_password` (wraz z ich `try`/`except`) w bloku `with _hash_slots:`. `simulate_password_check` przechodzi przez `verify_password`; `_DUMMY_PASSWORD_HASH` zostaje bez zmian.
3. Istniejące testy w `test_auth_concurrency.py` przechodzą bez zmian: podmieniają nazwy w `app.routers.auth`, które nadal wołają te funkcje. `make test`, `make lint` i `make typecheck` przechodzą.

### Task 9: Jeden worker uvicorn niezależnie od WEB_CONCURRENCY (B3)
**Commit:** fix: pin the API to one uvicorn worker regardless of WEB_CONCURRENCY

**Files:**
- Modify: `backend/Dockerfile`
- Modify: `Makefile`
- Modify: `scripts/stack_smoke.sh`

Warunek: BE-06 w `docs/testing/evidence/2026-11-27-patchpoint-final/results-baseline-dev-api.md` ma wynik `Fail`. W przeciwnym razie nie zmieniaj niczego i zakończ raportem `**Status:** ✅ Complete — not needed: BE-06 <wynik>`.

1. **Najpierw kontrola w smoke.** W `scripts/stack_smoke.sh`, części 1 po kontroli pip:
   - Kontener `patchpoint-smoke-workers` z `$PATCHPOINT_API_IMAGE`: `docker run -d --name patchpoint-smoke-workers --no-healthcheck --read-only --tmpfs /tmp -e WEB_CONCURRENCY=4 -e PATCHPOINT_DATABASE_PATH=/tmp/workers.db`. Błąd startu obsłuż przez `die`.
   - Czekaj do 30 s na `Uvicorn running on` w `docker logs`.
   - `count=$(docker top patchpoint-smoke-workers -o pid | tail -n +2 | wc -l)`, potem `docker rm -f` kontenera.
   - `count` równe 1 → `ok "obraz API uruchamia jeden proces uvicorn także przy WEB_CONCURRENCY=4"`. W przeciwnym razie `bad "obraz API: $count procesów przy WEB_CONCURRENCY=4, oczekiwano 1"`.
   - Dopisz `docker rm -f patchpoint-smoke-workers` do `cleanup()`.
   - Komentarz nad kontrolą: blokada logowania i zapisy SQLite zakładają jeden proces z jedną pętlą zdarzeń (`backend/app/routers/auth.py`, odczyt licznika i zapis próby bez `await`), a uvicorn czyta `WEB_CONCURRENCY` jako liczbę workerów.
   - `make images && make stack-smoke` → ta kontrola daje `[BŁĄD]`.
2. **`backend/Dockerfile`:** CMD przyjmuje postać `["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-server-header"]`. Nad nią komentarz: z tego samego powodu; `--workers` w poleceniu ma pierwszeństwo przed `WEB_CONCURRENCY`.
3. **`Makefile`:** w celu `run` dodaj `--workers 1` po `--port $(API_PORT)`. `backend/tests/test_client_ip.py` czyta argumenty przez `make -n run` i działa dalej.
4. **Sprawdzenia:**
   - `make images && make stack-smoke` — wszystkie kontrole `[OK]`, razem 29;
   - `WEB_CONCURRENCY=4 PATCHPOINT_DATABASE_PATH=$(mktemp -d)/w.db make run API_PORT=18101` wypisuje dokładnie jedną linię `Started server process`;
   - `make test` i `make shellcheck` przechodzą.

### Task 10: Poprawki ról Ansible base i docker (B4)
**Commit:** fix(deploy): fix base and docker role defects found in the container test

**Files:**
- Modify: `deploy/ansible/roles/base/tasks/main.yml`
- Modify: `deploy/ansible/roles/base/handlers/main.yml`
- Modify: `deploy/ansible/roles/docker/tasks/main.yml`
- Modify: `deploy/ansible/roles/docker/handlers/main.yml`

Warunek: `docs/testing/evidence/2026-11-27-patchpoint-final/results-ansible.md` ma co najmniej jedną kontrolę OPS-17 oznaczoną jako `Fail` z rozstrzygnięciem `role defect`. W przeciwnym razie nie zmieniaj niczego i zakończ raportem `**Status:** ✅ Complete — not needed: OPS-17 <wynik>`.

1. **Zasady poprawek:**
   - zmieniasz tylko cztery pliki z listy;
   - jedna minimalna zmiana na nieudaną kontrolę;
   - bez nowych zmiennych, ról ani zachowań spoza opisu w §9 `docs/faza-3-ops/README.md`.
2. **Poprawki z góry rozstrzygnięte:**
   - **Kontrola j)** (drugi przebieg zgłasza zmianę w „Zainstaluj Docker Engine i Docker Compose”) → dodaj `cache_valid_time: 3600` obok `update_cache: true`, tak jak w zadaniu „Zainstaluj pakiety bazowe” roli `base`.
   - **Kontrola a)** (handler „Przeładuj nftables” zawodzi, bo usługa jest nieaktywna przy pierwszym przebiegu) → `state: restarted` w tym handlerze. Drop-in ogranicza zatrzymanie do tabeli hosta, więc restart nie usuwa reguł Dockera.
   - **Każda inna kontrola** → najmniejsza zmiana w tych plikach, po której przechodzi. Jeśli takiej nie ma, opisz ją w raporcie zadania jako nienaprawioną.
3. **Weryfikacja:** po zmianach wykonaj OPS-17 na świeżym celu (nowy kontener i wolumen za każdym razem, najwyżej 3 próby), aż a)–j) przejdą. Potem `make ansible-lint` i sprzątanie celu. Dowody tego przebiegu zapisuje Task 12.

### Task 11: Dokumentacja — widoczność repozytorium, GHCR i odtwarzanie (B5)
**Commit:** docs: correct repository visibility and GHCR status and add the tested restore procedure

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `docs/faza-3-ops/README.md`

Każdy krok wykonaj tylko przy jego wyzwalaczu. Wyzwalacze odczytasz z `results-repo.md` (OPS-15) i `results-resilience-data.md` (OPS-10) w `docs/testing/evidence/2026-11-27-patchpoint-final/`. Gdy żaden się nie spełnia, nie zmieniaj niczego i zakończ raportem `**Status:** ✅ Complete — not needed`.

1. **OPS-15 wykazał rozjazd widoczności repozytorium.** W komentarzu `.github/workflows/ci.yml:13-15` zastąp zdanie „Repozytorium jest prywatne bez GitHub Advanced Security, więc SARIF trafia do artefaktów, nie do code scanning.” zdaniem „SARIF trafia do artefaktów przebiegu; potok nie wysyła go do code scanning.”. Zmienia się tylko komentarz.
2. **OPS-15 wykazał rozjazd stanu GHCR.** W §13 `docs/faza-3-ops/README.md`:
   - W punkcie o tagach `sha-<7>` zastąp „Odczyt digestu przez `docker buildx imagetools inspect` w `publish` i wdrożenie po digeście nie zostały sprawdzone na GHCR ani na serwerze (publikacja możliwa dopiero po scaleniu do `main`).” tekstem „Odczyt digestu przez `docker buildx imagetools inspect` w `publish` zadziałał w przebiegu `44694936930` na `main` (job `publish` `success`, [`dowody/ci.md`](dowody/ci.md)); wdrożenia po digeście nie sprawdzono na serwerze.”.
   - Punkt „Publikacja w GHCR (`publish`) zostanie sprawdzona dopiero po scaleniu do `main`.” zastąp tekstem „Publikację w GHCR sprawdził przebieg `44694936930` z 2026-11-20; obrazy z poprawek testów końcowych trafią do GHCR dopiero po scaleniu do `main`.”.
3. **OPS-10 ma wynik `Pass`.** W §10:
   - W wierszu „Kopię przechowuj poza serwerem. Procedura odtwarzania nie została opisana ani sprawdzona.” usuń drugie zdanie; pierwsze zostaje. Pod tym wierszem dodaj akapit „Odtworzenie z kopii (procedurę sprawdzono lokalnie w scenariuszu OPS-10 [raportu testów końcowych](../testing/reports/2026-11-27-patchpoint-final-report.md)). Wolumen jest usuwany, żeby obok odtworzonego pliku nie zostały pliki dziennika bieżącej bazy (`-journal`, `-wal`, `-shm`):”.
   - Dodaj blok `bash`:
     ```bash
     docker compose --project-directory /opt/patchpoint down
     docker volume rm patchpoint_api-data
     install -d -m 0755 /tmp/patchpoint-restore
     install -m 0644 ./patchpoint-RRRR-MM-DD.db /tmp/patchpoint-restore/patchpoint.db
     docker compose --project-directory /opt/patchpoint run --rm --no-deps -T -v /tmp/patchpoint-restore:/restore:ro --entrypoint python api -c "import shutil; shutil.copyfile('/restore/patchpoint.db', '/data/patchpoint.db')"
     rm -r /tmp/patchpoint-restore
     docker compose --project-directory /opt/patchpoint up -d --wait
     ```
   - W §13 zmień „kopie zapasowe wykonuje się ręcznie, a odtwarzanie nie jest opisane” na „kopie zapasowe i odtwarzanie wykonuje się ręcznie (procedury w sekcji 10)”.
   - Jeśli polecenia zapisane w OPS-10 różnią się od powyższych czymś poza nazwą projektu i ścieżkami, przenieś wersję z OPS-10.

### Task 12: Testy po poprawkach i odświeżenie dowodów Fazy 3
**Commit:** docs: re-test after the final fixes and refresh phase 3 evidence

**Files:**
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/retest.txt`
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/results-retest.md`
- Modify: `docs/faza-3-ops/dowody/jakosc.txt`
- Modify: `docs/faza-3-ops/dowody/testy.txt`
- Modify: `docs/faza-3-ops/dowody/obrazy.txt`
- Modify: `docs/faza-3-ops/dowody/semgrep.txt`
- Modify: `docs/faza-3-ops/dowody/trivy-fs.txt`
- Modify: `docs/faza-3-ops/dowody/trivy-obrazy.txt`
- Modify: `docs/faza-3-ops/dowody/smoke-stosu.txt`
- Modify: `docs/faza-3-ops/dowody/ansible-lint.txt`
- Modify: `docs/faza-3-ops/dowody/README.md`
- Modify: `docs/faza-3-ops/dowody/triaz-skanow.md`
- Modify: `docs/faza-3-ops/README.md`

1. **Ustal zastosowane poprawki.** W `git log --format=%s main..HEAD` szukaj tematów commitów zadań 7–11.
2. **OPS-01 w całości**, z tymi samymi poleceniami, co w tabeli `docs/faza-3-ops/dowody/README.md` (kolumna „Jak powstał”):
   - wyjście każdego polecenia nadpisuje odpowiedni plik `docs/faza-3-ops/dowody/*.txt`;
   - obraz API budujesz z `--no-cache` przed `make images` i `make trivy-images`;
   - plik `obrazy.txt` odtwarzasz poleceniami zapisanymi w jego nagłówkach;
   - linie podsumowań trafiają do `retest.txt`.
3. **Ponowne scenariusze zależnie od poprawek** (pozostałe nie są powtarzane):
   - zawsze: BE-02 i BE-03 na `dev`;
   - Task 7: BE-05 na `dev` oraz OPS-09 i OPS-10 na świeżym stosie;
   - Task 8: OPS-05 na świeżym stosie;
   - Task 9: BE-06 na `workers` (oczekiwany jeden `Started server process`);
   - Task 10: OPS-17 na świeżym celu.
4. **`results-retest.md`:** tabela `| ID | Baseline | After fixes | Fix commit | Evidence |` dla każdego powtórzonego scenariusza.
5. **`docs/faza-3-ops/dowody/README.md`:** wartości w kolumnie „Co dowodzi” z nowych wyjść — liczba testów i pokrycie, liczby plików ruff/mypy, reguły i pliki Semgrepa, liczba `[OK]` smoke, rozmiary obrazów, stan Trivy. Także tabela „Środowisko”: data, `git rev-parse --short HEAD` i wersja Dockera.
6. **`triaz-skanow.md`:** dopisz akapit `Podsumowanie po testach końcowych (<data>): …` z wynikami skanów.
7. **`docs/faza-3-ops/README.md`:**
   - §12: zaktualizuj punkty o testach, jakości, Semgrepie, Trivy fs, Trivy obrazów, smoke i Ansible.
   - §9 (zdanie o `ansible-lint` i `--syntax-check`) i §13 (punkt o niewykonanym playbooku), gdy OPS-17 przeszedł w bazie albo po Task 10: role `base` i `docker` sprawdzono na jednorazowym kontenerze systemd z Debianem 13 (OPS-17, link do raportu testów końcowych) — kolejność handlerów, `ExecStop=-`, reguły Dockera po restarcie nftables, SSH, zapora i idempotencja. Rola `patchpoint` (GHCR, wdrożenie) i `letsencrypt` nie były uruchamiane. Gdy OPS-17 nie przeszedł, wypisz nieudane kontrole.
   - Po Task 7: do punktu §13 o SQLite dopisz „Baza działa w trybie WAL: odczyty spoza API nie blokują zapisów; zapisuje nadal jeden proces.”.
   - Po Task 9: do tego samego punktu dopisz „API uruchamia jeden worker uvicorn (`--workers 1`), bo blokada logowania zakłada jedną pętlę zdarzeń.”.
   - Po Task 8: wiersz PERF-001 w tabeli §11 zmień na „zrealizowane: Argon2 poza pętlą zdarzeń i najwyżej 4 równoległe obliczenia (`PASSWORD_HASH_CONCURRENCY` w `backend/app/security.py`), poniżej `mem_limit` API; limit żądań dla logowania i rejestracji”.
8. **Skan sekretów, sprzątanie i usunięcie `$RUN`.**

### Task 13: CI na gałęzi delivery i draft PR
**Commit:** docs: record the CI run of the final test branch

**Files:**
- Create: `docs/testing/evidence/2026-11-27-patchpoint-final/ci.txt`
- Modify: `docs/faza-3-ops/dowody/ci.md`
- Modify: `docs/faza-3-ops/README.md`

1. **Push.** `BRANCH=$(git branch --show-current)`, potem `git push -u origin "$BRANCH"`.
   - Przy błędzie uwierzytelnienia: `gh auth setup-git` i jedna ponowna próba.
   - Jeśli push nadal się nie udaje: OPS-18 dostaje `Need info: credentials`, zapisz to w `ci.txt` i przejdź do kroku 5.
2. **Draft PR.** `gh pr create --draft --base main --head "$BRANCH" --title "Testy końcowe i poprawki po ocenie prowadzącego" --body-file "$RUN/pr-body.md"`.
   - Treść `pr-body.md`: lista `git log --format='- %s' origin/main..HEAD` oraz ścieżki planu testów i raportu.
   - Gdy PR dla gałęzi już istnieje, użyj go (`gh pr view "$BRANCH" --json url`).
3. **Czekanie na przebieg.** `SHA=$(git rev-parse HEAD)`. Co 30 s, najdłużej 40 min, wołaj `gh run list --branch "$BRANCH" --event pull_request --json databaseId,headSha,status,conclusion`, aż przebieg dla `SHA` ma `status` `completed`.
4. **Zapis w `ci.txt`:**
   - `gh run view <id> --json conclusion,createdAt,headSha,event,jobs` — dla jobów nazwa, wynik, początek i koniec;
   - `gh api repos/l3x1cn/patchpoint/actions/runs/<id>/artifacts --jq '.artifacts[] | [.name, .size_in_bytes] | @tsv'`;
   - przy porażce `gh run view <id> --log-failed | tail -n 80`.
5. **`docs/faza-3-ops/dowody/ci.md`:**
   - zaraz po akapicie wstępnym nowa sekcja `## Przebieg końcowy (testy końcowe)` z tabelami „Przebieg” (PR, gałąź, commit, adres przebiegu, zdarzenie, data, wynik), „Joby” (wynik, czas) i „Artefakty”;
   - pierwsze zdanie wstępu wskazuje ten przebieg jako ostatni.
6. **`docs/faza-3-ops/README.md`:** punkt CI w §12 zastąp opisem nowego przebiegu, a do akapitu „Wynik” w §8 dopisz zdanie z jego numerem.
7. **Wynik OPS-18** według planu testów. Porażka przebiegu jest zapisywana, a nie naprawiana.

### Task 14: Raport końcowy
**Commit:** docs: add the final test report with the review remark verification

**Files:**
- Create: `docs/testing/reports/2026-11-27-patchpoint-final-report.md`
- Modify: `README.md`

1. **Wejście:** wszystkie `results-*.md`, pliki dowodów w `docs/testing/evidence/2026-11-27-patchpoint-final/` i plan testów. Przeczytaj `skill://qa:report-format`.
2. **Raport po angielsku**, w strukturze `qa:report-format`:
   1. `# Test Report: patchpoint-final`.
   2. `## Summary`:
      - `Total | Pass | Fail | Skip | Need info` dla scenariuszy `contract`, z wynikiem po poprawkach tam, gdzie scenariusz powtórzono;
      - osobna linia `Probes: Confirmed N | Not confirmed N | Partially confirmed N`;
      - Plan, `Plan provenance: hand-written`, Date, Duration;
      - `Accounts: registered N (deleted 0, left N, manual 0)` z dopiskiem, że wszystkie konta powstały w bazach usuniętych po testach.
   3. `## Setup gaps` — tylko przy `Need info`.
   4. `## Issues Found` — osobny `### [SEVERITY] QA-NNN: <title>` dla każdego bazowego `Fail` i każdej sondy, która ujawniła defekt. Numeracja w kolejności planu: FE, BE, OPS.
      - Pola: `**ID:**`, `**Location:**` (`path:line`), `**Category:** Testing`, `**Problem:**`, `**Impact:**`, `**Remediation:**`, `**Scenario:**`, a dla BE także `**Response:**`.
      - `**Problem:**` zawiera Expected skopiowane z planu razem z cytatem, Actual z dowodu oraz `Refutation: re-verified: <yes|no>; env: <instance|stack|target>; evidence: <file>`.
      - Zgłoszenia naprawione w zadaniach 7–11 mają jako pierwszą linię pod nagłówkiem `**Status:** ✅ Fixed (<data>)`, a w Remediation temat commitu poprawki.
   5. `## Detailed Results` — każdy scenariusz dokładnie raz, w kolejności planu: `### Pass|Fail|Skip|Need info: <ID>: <title>` dla `contract` oraz `### Confirmed|Not confirmed|Partially confirmed: <ID>: <title>` dla `probe`. Pod nagłówkiem jedna linia z odwołaniem do dowodu.
   6. `## Before and after fixes` — tabela z `results-retest.md`.
   7. `## Review remark verification` — wiersze R1.1–R3.10 z kolumnami: polski tytuł uwagi z „Macierzy uwag”, scenariusze, wynik, działanie. Działanie to `fixed in <commit subject>`, `development item, not implemented by decision` albo `no action`.
   8. `## Not covered` — pozycje z sekcji „Out of harness scope” planu testów.
3. **`README.md`**, sekcja „Dokumentacja”: dopisz po pozycjach Fazy 3:
   - `- [Plan testów końcowych](docs/testing/plans/2026-11-27-patchpoint-final-test-plan.md)`;
   - `- [Raport testów końcowych z weryfikacją uwag prowadzącego](docs/testing/reports/2026-11-27-patchpoint-final-report.md)`.
4. **Kontrola:**
   - każdy identyfikator planu testów występuje dokładnie raz w `## Detailed Results`;
   - liczby w Summary zgadzają się z tą sekcją;
   - raport nie zawiera haseł ani tokenów.

## Critical files & anchors

| Plik | Miejsce | Dlaczego |
|---|---|---|
| `backend/app/database.py` | `connect` (`:118-122`), `init_db` (`:275-282`) | B1: WAL i jawny busy timeout; tu powstaje 500 przy zablokowanym commicie |
| `backend/app/security.py` | `_password_hasher`, `hash_password`, `verify_password` (`:11-28`) | B2: semafor Argon2; testy z `test_auth_concurrency.py` podmieniają nazwy w routerze |
| `backend/app/routers/auth.py` | `login` (`:86-154`), odczyt licznika `:94`, zapis próby `:108` | gwarancja limitu prób, sprawdzana w BE-03 i BE-06 |
| `scripts/stack_smoke.sh` | `cleanup` (`:37-46`), część 1 (`:73-94`) | B3: nowa kontrola procesów i sprzątanie kontenera |
| `docs/faza-3-ops/README.md` | §10 (`:262-270`), §12 (`:297-306`), §13 (`:312-329`) | B5 oraz odświeżenie wyników po testach |

## Verification

Kroki wykonuje orkiestrator w katalogu głównym repozytorium, na gałęzi delivery, po zadaniu 14:

1. `make lint && make typecheck && make test` — przechodzą, łącznie z nowymi testami z zadań 7–8, jeśli powstały.
2. `make semgrep && make trivy-fs && make shellcheck && make actionlint && make ansible-lint` — przechodzą.
3. Każdy identyfikator planu występuje dokładnie raz w raporcie:
   ```bash
   python3 - <<'PY'
   import re
   plan = open("docs/testing/plans/2026-11-27-patchpoint-final-test-plan.md", encoding="utf-8").read()
   report = open("docs/testing/reports/2026-11-27-patchpoint-final-report.md", encoding="utf-8").read()
   ids = re.findall(r"^### ((?:FE|BE|OPS)-\d{2}):", plan, re.M)
   detailed = report.split("## Detailed Results", 1)[1].split("\n## ", 1)[0]
   got = re.findall(r"^### [A-Za-z ]+: ((?:FE|BE|OPS)-\d{2}):", detailed, re.M)
   assert len(ids) == 32 and sorted(ids) == sorted(got), (len(ids), sorted(set(ids) ^ set(got)))
   print("ok", len(ids))
   PY
   ```
   Oczekiwane wyjście: `ok 32`.
4. Higiena sekretów. Oba polecenia mają nie zwrócić nic:
   - `grep -rnE '(session|__Host-session)=[A-Za-z0-9_-]{20,}' docs/testing/evidence/2026-11-27-patchpoint-final docs/testing/reports/2026-11-27-patchpoint-final-report.md`;
   - `grep -rn 'PATCHPOINT_DEMO_PASSWORD=' docs/testing/evidence/2026-11-27-patchpoint-final`.
5. Brak pozostałości. Wszystkie trzy polecenia mają nie zwrócić nic:
   - `docker ps -a --format '{{.Names}}' | grep -E '^(patchpoint-final-|patchpoint-smoke|pp-ansible-target|pp-verify-)'`;
   - `docker volume ls -q | grep -E '^(patchpoint-final_|pp-ansible-docker$)'`;
   - `ss -ltn | grep -E ':(1810[0-2]|28080|28443|2222)\b'`.
6. Jeśli Task 7 zmienił kod, nowe zachowanie: instancja `dev` z sekcji Setup planu testów na 18100. Zarejestruj użytkownika, uruchom czytelnika z BE-05 (`BEGIN`, `SELECT`, sen 15 s) i w tym czasie wyślij logowanie z błędnym hasłem. Oczekiwane: `401` z czasem < 1 s, a `sqlite3 -readonly <baza> 'PRAGMA journal_mode'` zwraca `wal`.
7. Jeśli Task 9 zmienił kod:
   ```bash
   docker run -d --name pp-verify-workers --no-healthcheck --read-only --tmpfs /tmp \
     -e WEB_CONCURRENCY=4 -e PATCHPOINT_DATABASE_PATH=/tmp/v.db patchpoint-api:local
   ```
   Gdy w `docker logs pp-verify-workers` pojawi się `Uvicorn running on`, `docker top pp-verify-workers -o pid | tail -n +2 | wc -l` zwraca `1`. Potem `docker rm -f pp-verify-workers`.
8. `gh pr view "$(git branch --show-current)" --json isDraft,state --jq '[.isDraft, .state]'` zwraca `[true,"OPEN"]`. Wynik przebiegu wpisany w `docs/faza-3-ops/dowody/ci.md` równa się `gh run view <id> --json conclusion`.
9. `git status --porcelain` — puste.

## Assumptions & contingencies

- **Testy ręczne zamiast `/qa:run`.** Silnik wymaga portów 8080 i 8443, a zajmują je klaster kind i stos `patchpoint` użytkownika. Plan nie zatrzymuje tych kontenerów; scenariusze FE i BE wykonują się ręcznie na portach 28080, 28443 i 18100–18102, a raport ma format `qa:report-format`.
- **Krok QA w delivery.** Po weryfikacji delivery uruchamia `/qa:run` dla zmian kodu z zadań 7–9. Zatrzyma się na starcie usług z powodu portów 8080 i 8443, chyba że wcześniej zatrzymasz `secure-k8s-aiops-*` i projekt `patchpoint`. Przy pytaniu wybierz „Continue to the final review”: te zmiany pokrywa raport końcowy.
- **Nowa podatność w bazie Trivy.** Jeśli w OPS-01, w Task 12 albo w CI pojawi się nowe znalezisko HIGH lub CRITICAL z poprawką, zostaje zapisane jako QA-NNN. Nie podbijamy obrazu ani nie dodajemy wyjątku w tej delivery.
- **Zadanie naprawcze bez wyzwalacza.** Gdy wyzwalacz nie wystąpił, zadanie nie zmienia plików, a delivery zapyta o dalszy krok. Wybierz „Skip this task”.
- **Nieoczekiwane porażki** spoza mapy napraw dostają QA-NNN z propozycją naprawy. Można je później naprawić przez `/code-review:fix-report docs/testing/reports/2026-11-27-patchpoint-final-report.md`.
- **Push.** Wypychana jest tylko gałąź `delivery/patchpoint-final-testing` i otwierany draft PR. `main` nie jest zmieniany, a `publish` nie działa. Commity zadań 13 i 14 oraz poprawki z przeglądu kodu zostają lokalnie, do wypchnięcia przez użytkownika.
- **Prawdziwy sekret w historii.** Gdy gitleaks znajdzie prawdziwy sekret, historia publicznego repozytorium nie jest przepisywana. Rotacja to decyzja użytkownika, wskazana w raporcie (HIGH) i w podsumowaniu delivery.
