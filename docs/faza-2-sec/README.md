# Raport z Fazy 2 (SEC) — PatchPoint

Dokument opisuje wynik Fazy 2 projektu „AI-Driven DevSecOps” (Scenariusz 5: Menadżer Zadań IT): audyt bezpieczeństwa kodu z Fazy 1 z pomocą AI, weryfikację znalezisk i naprawę aplikacji. Jest jednocześnie Sekcją Sec końcowego Raportu Architektonicznego DevSecOps: zestawieniem luk wykrytych w Fazie 1, opisem wektorów ataku i mechanizmów naprawy. Powiązane dokumenty: [audyt Red Team](audyt-red-team.md), [threat model](threat-model.md), [dowody](dowody/README.md), [rejestr słabości Fazy 1](../faza-1-dev/rejestr-slabosci.md).

## 1. Cel fazy

Punkty „Faza 2: SEC” z instrukcji kursu:

> - Zmieńcie rolę i stwórzcie z AI "Wirtualnego Red Teamera". Przeprowadźcie statyczną analizę wygenerowanego kodu (SAST), prosząc o wskazanie luk z listy OWASP Top 10.
> - Zweryfikujcie poprawność wykrytych podatności (Threat Modeling) dla Waszego konkretnego wektora ataku opisanego w scenariuszu.
> - Wykorzystajcie AI do naprawienia kodu (np. wdrożenie parametryzacji zapytań SQL, sanityzacji wejścia, ukrycia ścieżek). Sprawdźcie, czy połatana aplikacja nadal poprawnie funkcjonuje.

| Wymaganie | Realizacja | Dowód |
|---|---|---|
| „Wirtualny Red Teamer” i SAST według OWASP Top 10 | ślepy audyt AI (16 luk RT-01…RT-16) oraz klasyczny SAST: Ruff z regułami `S` (Bandit) | [`audyt-red-team.md`](audyt-red-team.md), [`audyt-red-team-wynik.md`](audyt-red-team-wynik.md), [`dowody/ruff-s-faza-1.txt`](dowody/ruff-s-faza-1.txt) |
| Weryfikacja podatności (Threat Modeling) | STRIDE na diagramie przepływu danych, werdykty dla każdego znaleziska, skrypt PoC uruchomiony na kodzie Fazy 1 | [`threat-model.md`](threat-model.md), [`dowody/poc-faza-1.txt`](dowody/poc-faza-1.txt) |
| Naprawa kodu z AI | poprawki w backendzie, frontendzie i skryptach, opisane w sekcjach 4 i 6 | sekcje 4 i 6 tego dokumentu |
| Połatana aplikacja działa | testy, scenariusz end-to-end i ten sam PoC na kodzie Fazy 2 | [`dowody/testy.txt`](dowody/testy.txt), [`dowody/demo.txt`](dowody/demo.txt), [`dowody/poc-faza-2.txt`](dowody/poc-faza-2.txt) |

## 2. Metoda pracy z AI

Audyt wykonał osobny agent AI tylko do odczytu, który widział wyłącznie kod `backend/app/**` i `frontend/**`: ślepy audyt przeprowadzono przed napisaniem planu, bez rejestru słabości z Fazy 1. Znaleziska zweryfikowano w threat modelu (kod, uruchomienie bibliotek, porównanie z rejestrem i z code review Fazy 1). Poprawki napisali agenci delivery, zadanie po zadaniu, a wynik każdego zadania przejrzał osobny agent-recenzent. Przed naprawą i po niej uruchomiono ten sam skrypt PoC (`scripts/security_check.sh`): 22 sprawdzenia `[PODATNE]` na kodzie Fazy 1 i 22 `[NAPRAWIONE]` na kodzie Fazy 2. Po zakończeniu delivery przewidziano jeszcze QA i końcowy code review.

## 3. Wyniki audytu i porównanie z rejestrem

Szczegóły w [`threat-model.md`](threat-model.md), sekcje 4 i 5:

- audyt AI trafił 18 z 18 pozycji rejestru słabości (16 znalezisk, bo RT-07 obejmuje W-09…W-11, RT-10 obejmuje W-01 i W-02, a W-12 rozpada się na RT-09 i RT-12), bez fałszywych trafień; wszystkie 16 znalezisk zespół uznał za potwierdzone;
- klasyczny SAST (Ruff `S`) wskazał 2 z 18 pozycji (W-07 i W-08 przez S324), 1 fałszywie dodatnie (S608 w `update_ticket`) i pominął 16, w tym SQL injection z W-14;
- audyt wykrył też rzeczy spoza rejestru: brak nagłówków bezpieczeństwa i CSP (RT-16), `OverflowError` dla identyfikatorów większych niż 2⁶³−1 (RT-13) oraz, częściowo, brak limitów (SEC-017) i jawne tokeny w bazie (SEC-020).

## 4. Zestawienie luk wykrytych w Fazie 1 i mechanizmów naprawy

Wszystkie pozycje W-01…W-18 oraz dodatkowe znaleziska z audytu i code review Fazy 1 (SEC-017, SEC-020, SEC-021, SEC-022). Ścieżki są względem `backend/app/` (z wyjątkiem plików frontendu i konfiguracji), testy względem `backend/tests/`. Kolumna OWASP odnosi się do listy OWASP Top 10:2025.

| Luka | Audyt | OWASP Top 10:2025 | Wektor | Mechanizm naprawy | Gdzie | Testy regresyjne | PoC |
|---|---|---|---|---|---|---|---|
| W-01 gadatliwy błąd bazy | RT-10 | A10 | Information Disclosure | ogólne 500 `{"detail", "error_id"}`; SQL bez parametrów i traceback tylko w logu `patchpoint.errors` | `main.py`, `audit.py` | `test_errors.py::test_database_error_returns_generic_body_and_logs_details` | W-01 |
| W-02 komunikat UNIQUE | RT-10 | A10 | Information Disclosure | stały 409 „Username is already taken” i zdarzenie `registration_conflict` | `routers/auth.py` | `test_auth.py::test_register_rejects_duplicate_username_without_database_details` | W-02 |
| W-03 debug i `/docs` | RT-13 | A02 | Information Disclosure | bez trybu debug; dokumentacja tylko przy `PATCHPOINT_DOCS_ENABLED=true`; handler `Exception` | `main.py`, `config.py` | `test_platform.py::test_api_docs_are_disabled_by_default`, `test_platform.py::test_api_docs_can_be_enabled_for_development`, `test_errors.py::test_unhandled_exception_returns_generic_json` | W-03 |
| W-04 health | RT-14 | A01 | Information Disclosure | `{"status": "ok"}` | `routers/health.py` | `test_health.py::test_health_reports_only_status` | W-04 |
| W-05 enumeracja kont | RT-12 | A07 | Information Disclosure / Broken Authentication | jednolite 401; weryfikacja na stałym hashu dla nieznanego loginu | `routers/auth.py`, `security.py` | `test_auth.py::test_login_failures_are_indistinguishable` | W-05 |
| W-06 hash w API | RT-11 | A01 | Information Disclosure | `UserResponse` bez hasha, jawne listy kolumn | `schemas.py`, `routers/auth.py`, `sessions.py` | `test_auth.py::test_user_responses_never_include_password_hash` | W-06 |
| W-07 MD5 | RT-08 | A04 | Broken Authentication | Argon2id (`argon2-cffi`, sól per hasło); hashe MD5 odrzucane | `security.py` | `test_database.py::test_password_hashes_use_argon2id`, `test_database.py::test_legacy_md5_hash_is_rejected` | W-07 |
| W-08 przewidywalny token | RT-03 | A07 | Broken Authentication | `secrets.token_urlsafe(32)` (256 bitów) | `security.py`, `sessions.py` | `test_sessions.py::test_session_tokens_are_random_and_stored_hashed` | W-08 |
| W-09 brak wygasania | RT-07 | A07 | Broken Authentication | 30 min bezczynności, 8 h maksymalnie, `Max-Age` ciasteczka | `schema.sql`, `sessions.py` | `test_sessions.py::test_idle_session_expires`, `test_sessions.py::test_session_expires_after_absolute_lifetime`, `test_sessions.py::test_activity_extends_idle_window` | W-09 |
| W-10 wylogowanie | RT-07 | A07 | Broken Authentication | usunięcie sesji na serwerze i ciasteczka | `routers/auth.py`, `sessions.py` | `test_sessions.py::test_logout_invalidates_session_on_server` | W-10 |
| W-11 flagi, token w JSON, Bearer | RT-07, RT-03 | A02 | Broken Authentication | `HttpOnly; Secure; SameSite=Strict`; odpowiedź `{user}`; tylko ciasteczko | `routers/auth.py`, `dependencies.py` | `test_auth.py::test_session_cookie_has_security_attributes`, `test_auth.py::test_login_returns_user_without_token`, `test_auth.py::test_bearer_header_is_not_accepted` | W-11 |
| W-12 konta domyślne, hasła, limit prób | RT-09, RT-12 | A07 | Broken Authentication | seed tylko na żądanie z `PATCHPOINT_DEMO_PASSWORD`, bez konta `admin`; hasła 15–128 znaków bez loginu; 5 prób w 15 min, potem 429 | `config.py`, `database.py`, `schemas.py`, `security.py`, `sessions.py` | `test_auth.py::test_register_enforces_password_policy`, `test_auth.py::test_login_is_blocked_after_repeated_failures`, `test_auth.py::test_old_login_failures_do_not_block`, `test_auth.py::test_successful_login_clears_failure_count`, `test_auth.py::test_demo_accounts_use_configured_password`, `test_database.py::test_demo_seed_requires_password`, `test_database.py::test_demo_seed_rejects_weak_password` | W-12 |
| W-13 CORS | RT-06 | A02 | CORS | lista `PATCHPOINT_CORS_ORIGINS` bez `*`; metody GET/POST/PATCH; nagłówek `Content-Type` | `main.py`, `config.py` | `test_cors.py` (10 testów, m.in. `test_preflight_rejects_unknown_origin`, `test_wildcard_origin_is_rejected_in_settings`) | W-13 |
| W-14 SQL injection | RT-01 | A05 | Information Disclosure | statyczne zapytanie z parametrami, `LIKE … ESCAPE '\'` | `routers/tickets.py` | `test_ticket_security.py::test_search_input_is_not_interpreted_as_sql`, `test_ticket_security.py::test_search_treats_like_wildcards_literally` | W-14 |
| W-15 mass assignment | RT-02 | A08 | Broken Authentication | `extra="forbid"`, rola zawsze `employee` | `schemas.py`, `routers/auth.py` | `test_auth.py::test_register_rejects_role_field` | W-15 |
| W-16 IDOR | RT-04 | A01 | Information Disclosure | `_visible_ticket()`: 404 dla cudzych zgłoszeń i zdarzenie `access_denied` | `routers/tickets.py` | `test_ticket_security.py::test_employee_cannot_read_foreign_ticket`, `test_ticket_security.py::test_employee_cannot_comment_on_foreign_ticket`, `test_ticket_security.py::test_foreign_ticket_access_is_logged` | W-16 |
| W-17 XSS | RT-05 | A05 | Broken Authentication | DOM budowany przez `textContent` i `new Option`, CSP | `frontend/app.js`, `frontend/index.html` | brak testu automatycznego; weryfikacja UI w planie, statyczne sprawdzenie w PoC | W-17 |
| W-18 brak logów | RT-15 | A09 | wykrywalność ataków | zdarzenia JSON w loggerze `patchpoint.security` (tabela w sekcji 6) | `audit.py` i routery | `test_auth.py::test_authentication_events_are_logged_without_secrets`, `test_auth.py::test_registration_events_are_logged`, `test_ticket_security.py::test_ticket_updates_are_audited` | W-18 |
| SEC-017 limity i paginacja | CWE-770 (odnotowane w audycie) | A06 | dostępność | `max_length` pól, 64 KiB ciała żądania (413), `limit` ≤ 100 i `offset` | `schemas.py`, `main.py`, `routers/tickets.py` | `test_platform.py::test_oversized_request_body_is_rejected`, `test_ticket_security.py::test_ticket_list_is_paginated`, `test_ticket_security.py::test_pagination_bounds_are_validated`, `test_ticket_security.py::test_ticket_text_fields_have_length_limits` | SEC-017 |
| SEC-002 komentarze bez limitu (code review Fazy 2) | CWE-770 | A06 | dostępność | szczegóły zgłoszenia zwracają najnowsze 50 komentarzy (`COMMENTS_IN_DETAIL_MAX`) i `comment_count`; UI pokazuje „Wyświetlono ostatnie N z M komentarzy” | `routers/tickets.py`, `schemas.py`, `frontend/app.js` | `test_ticket_security.py::test_ticket_detail_returns_only_newest_comments_with_total`, `test_ticket_security.py::test_ticket_detail_counts_all_comments_below_the_limit` | — |
| SEC-020 jawne tokeny | rekomendacja w RT-03 | A04 | Broken Authentication | w bazie tylko SHA-256 tokenu | `sessions.py`, `schema.sql` | `test_sessions.py::test_session_tokens_are_random_and_stored_hashed` | SEC-020 |
| SEC-021 nagłówki | RT-16 | A02 | mitigacja XSS | `SecurityHeadersMiddleware` w API i CSP w UI | `middleware.py`, `frontend/index.html` | `test_platform.py::test_api_responses_carry_security_headers`, `test_platform.py::test_non_api_responses_skip_api_only_headers`, `test_platform.py::test_cors_preflight_carries_security_headers`, `test_platform.py::test_unhandled_exception_response_carries_security_headers` | SEC-021 |
| SEC-022 `/tmp` w konfiguracji QA | poza zakresem audytu | A02 | narzędzia | katalog `.av/run/` (0700, właściciel), ignorowany przez git | `.av/config.toml`, `.gitignore` | weryfikacja planu | — |
| `OverflowError` (nowe) | RT-13 | A10 | Information Disclosure | identyfikatory w zakresie 1…2⁶³−1 (poza zakresem 422), handler `Exception` | `routers/tickets.py`, `schemas.py`, `main.py` | `test_ticket_security.py::test_out_of_range_ids_are_rejected` | RT-13 |

### Uwagi jakościowe z code review Fazy 1

| ID | Zmiana |
|---|---|
| ARCH-001 | `transaction()` i `run()` w `database.py`; komentarz i `updated_at` zapisywane atomowo; seed w jednej transakcji |
| ARCH-002 | reset formularzy i komunikatów przy wylogowaniu; widok zmienia się dopiero po udanym `POST /logout`; 401 w trakcie pracy wraca do ekranu logowania |
| MAINT-001 | `DEMO_USERS`, `DEMO_TICKETS`, `DEMO_COMMENTS` i `_user_id()` w `database.py` |
| MAINT-002 | `_visible_ticket()` i statyczne `UPDATE … COALESCE` w `routers/tickets.py` |
| MAINT-003 | `create_app` bez aliasu `app_settings` |
| MAINT-004 | listy wyboru w UI wypełniane z map etykiet w `app.js` |
| MAINT-005 | `tests/support.py`, fikstura `seeded_settings`, asercje statusów logowań |
| DOC-001 | README z `docs/testing/`, `docs/reviews/`, `.av/` i linkami do raportów |

## 5. Wektory ataku

Łańcuchy ID-1, BA-1…BA-4 i CORS-1 opisano krok po kroku w [`threat-model.md`](threat-model.md), sekcja 6. Poniżej skrót „przed” i „po” dla trzech wektorów scenariusza, a na końcu sekcji diagram sesji w połatanej aplikacji.

### Information Disclosure

Przed: apostrof w parametrze `search` powodował błąd SQL, a odpowiedź 500 zawierała pełne zapytanie z JOIN-ami, ścieżkę bazy i traceback; ta podpowiedź pozwalała ułożyć `UNION SELECT` z tabel `sessions` i `users` (ID-1). Pracownik mógł też czytać cudze zgłoszenia, a `/api/health`, `/docs` i `password_hash` w `/api/auth/me` ujawniały środowisko i dane uwierzytelniające. Po: parametryzowane zapytanie z `ESCAPE` zamyka wstrzyknięcie; każdy błąd 500 to `{"detail": "Internal server error", "error_id": "<uuid>"}`, a szczegóły trafiają tylko do loga; cudze zgłoszenia dają 404, health zwraca `{"status": "ok"}`, dokumentacja API jest domyślnie wyłączona, a odpowiedzi nie mają hasha.

### Broken Authentication

Przed: rejestracja przyjmowała `"role": "agent"` (BA-4), konto `admin`/`admin123` i brak limitu prób pozwalały zgadywać hasła, a komunikaty 404 i 401 ujawniały istniejące loginy (BA-1). Token sesji był `md5(login:czas)`, ważny bezterminowo, zwracany w JSON i przyjmowany jako `Bearer` (BA-2), a XSS w zgłoszeniu mógł go wykraść z ciasteczka bez `HttpOnly` (BA-3). Po: rola jest zawsze `employee`, a nieznane pola dają 422; nie ma kont domyślnych, a hasło ma 15–128 znaków i nie zawiera loginu; błędy logowania są jednolite (401), a po 5 nieudanych próbach przez 15 minut odpowiada 429; token jest losowy, w bazie leży jego SHA-256, sesja wygasa po 30 minutach bezczynności lub 8 godzinach, a ciasteczko ma `HttpOnly; Secure; SameSite=Strict`; UI renderuje dane przez `textContent` i ma CSP.

### CORS

Przed: API z `allow_origins=["*"]` i `allow_credentials=True` odbijało dowolny `Origin`, więc obca strona na innym porcie `localhost` (ten sam site, więc ciasteczko `Lax` było wysyłane) mogła odczytać `/api/auth/me` i listę zgłoszeń (CORS-1). Po: dozwolone originy pochodzą z konfiguracji (domyślnie tylko `http://patchpoint.localhost:5500`, `*` odrzuca walidacja ustawień), dozwolone są metody GET/POST/PATCH i nagłówek `Content-Type`, a preflight z obcego originu dostaje 400 bez `Access-Control-Allow-Origin`. Ciasteczko `SameSite=Strict` dodatkowo odcina żądania z innych witryn. UI i API działają lokalnie pod `patchpoint.localhost`, osobną witryną od `localhost`, bo ciasteczko hosta `localhost` trafiałoby do każdej aplikacji na innym porcie (CORS-2, SEC-001). Żądanie z nagłówkiem `Origin` spoza listy (także proste, np. `POST /api/auth/logout`) dostaje 403 i nie jest przetwarzane; żądania bez `Origin` (np. z `curl`) przechodzą bez zmian.

```mermaid
sequenceDiagram
    participant B as Przeglądarka (http://patchpoint.localhost:5500)
    participant API as API (http://patchpoint.localhost:8000)
    participant DB as SQLite
    B->>API: OPTIONS /api/auth/login (Origin: http://patchpoint.localhost:5500)
    API-->>B: 200, Access-Control-Allow-Origin = http://patchpoint.localhost:5500
    B->>API: POST /api/auth/login {username, password}
    API->>DB: login_failures (limit prób), users (Argon2id)
    API->>DB: INSERT sessions (token_hash = SHA-256, expires_at, last_seen_at)
    API-->>B: 200 {user} + Set-Cookie: session; HttpOnly; Secure; SameSite=Strict; Max-Age=28800
    B->>API: GET /api/tickets?limit=50&offset=0 (Cookie: session)
    API->>DB: sesja aktywna? (30 min bezczynności, 8 h maksymalnie)
    API-->>B: 200 [zgłoszenia] + nagłówki bezpieczeństwa
    B->>API: POST /api/auth/logout
    API->>DB: DELETE sessions
    API-->>B: 200 + Set-Cookie: session=""; Max-Age=0
```

## 6. Mechanizmy naprawy

- **Parametryzacja SQL.** Lista zgłoszeń używa jednego statycznego zapytania `LIST_TICKETS_SQL` z parametrami nazwanymi; wzorzec `LIKE` buduje `escape_like()` z `ESCAPE '\'`, więc `%` i `_` są znakami dosłownymi. Aktualizacja zgłoszenia to statyczne `UPDATE … COALESCE`, bez składania listy kolumn (`backend/app/routers/tickets.py`). Ruff z regułami `S` nie zgłasza już żadnych diagnostyk.
- **Kontrola dostępu do obiektów.** `_visible_ticket()` jest jedynym miejscem, które sprawdza istnienie i własność zgłoszenia, więc odczyt, komentarz i aktualizacja zachowują się tak samo; cudze zgłoszenie daje identyczne 404 jak nieistniejące i zdarzenie `access_denied`. Role sprawdza zależność `AgentUser` (`backend/app/dependencies.py`).
- **Argon2id i polityka haseł.** Hasła haszuje `argon2-cffi` z parametrami domyślnymi biblioteki (Argon2id, sól per hasło); stary hash MD5 nie przechodzi weryfikacji. Polityka (`password_policy_violation` w `backend/app/security.py`) wymaga 15–128 znaków i hasła niezawierającego loginu; 15 znaków to minimum z NIST SP 800-63B-4 dla hasła jako jedynego czynnika, a górna granica 128 znaków spełnia zalecenie, by weryfikator dopuszczał co najmniej 64 znaki.
- **Sesje.** Token to `secrets.token_urlsafe(32)`, w bazie leży tylko jego SHA-256 (`token_hash`), a każda sesja ma `created_at`, `last_seen_at` i `expires_at` (30 minut bezczynności, 8 godzin maksymalnie). Wylogowanie usuwa wiersz sesji na serwerze, a ciasteczko ma `HttpOnly; Secure; SameSite=Strict`. Nagłówek `Authorization` nie jest już obsługiwany (`backend/app/sessions.py`, `backend/app/routers/auth.py`).
- **Ograniczenie prób logowania.** Nieudane próby trafiają do tabeli `login_failures`; po 5 próbach w 15 minut dla danego loginu API odpowiada 429 z `Retry-After`, a udane logowanie czyści licznik. Próba jest zapisywana przed weryfikacją hasła (bez `await` między sprawdzeniem blokady a zapisem), a udane logowanie ją usuwa, więc równoległe zgadywania nie przekraczają limitu (`test_auth_concurrency.py::test_concurrent_wrong_guesses_cannot_exceed_lockout`). Dla nieznanego loginu hasło jest weryfikowane na stałym hashu (`simulate_password_check`), co wyrównuje czas odpowiedzi.
- **CORS.** Dozwolone originy pochodzą z `PATCHPOINT_CORS_ORIGINS`, a wartość `*` jest odrzucana przy starcie; dozwolone metody i nagłówki ograniczono do GET/POST/PATCH i `Content-Type`. `OriginCheckMiddleware` odpowiada 403 `{"detail": "Origin not allowed"}` na każde żądanie z nagłówkiem `Origin` spoza listy, bez wywołania aplikacji (żądania bez `Origin` przechodzą), a `CORSMiddleware` leży na zewnątrz niego i sam odpowiada na preflight; najbardziej zewnętrzny jest `SecurityHeadersMiddleware`, więc nagłówki bezpieczeństwa obejmują także odpowiedź na preflight (`backend/app/main.py`, `backend/app/middleware.py`, `backend/app/config.py`).
- **Nagłówki bezpieczeństwa i CSP.** `SecurityHeadersMiddleware` dodaje `X-Content-Type-Options`, `X-Frame-Options` i `Referrer-Policy` do wszystkich odpowiedzi, a `Content-Security-Policy` i `Cache-Control: no-store` do odpowiedzi `/api/` (`backend/app/middleware.py`), a odpowiedź 500 wysyłaną przez `ServerErrorMiddleware` poza middleware uzupełnia o te same nagłówki `internal_error_handler` (`backend/app/main.py`). UI ma CSP w znaczniku `<meta>` (`frontend/index.html`).
- **Obsługa błędów.** Jeden handler `internal_error_handler` obsługuje `DatabaseError` i `Exception`: loguje szczegóły z `error_id` w `patchpoint.errors`, klientowi zwraca ogólny komunikat. `DatabaseError` nie przechowuje już parametrów zapytania, więc nie trafiają one do logów (`backend/app/main.py`, `backend/app/database.py`).
- **Walidacja wejścia i limity.** Modele wejściowe mają `extra="forbid"` i limity długości pól, identyfikatory w ścieżce mieszczą się w 1…2⁶³−1, lista zgłoszeń ma `limit` ≤ 100, szczegóły zgłoszenia zwracają co najwyżej 50 najnowszych komentarzy wraz z `comment_count`, a ciało żądania jest ograniczone do 64 KiB (`RequestBodyLimitMiddleware`, odpowiedź 413) (`backend/app/schemas.py`, `backend/app/routers/tickets.py`).
- **Bezpieczne renderowanie DOM.** `frontend/app.js` buduje elementy przez `createElement`, `textContent` i `new Option`; nie używa `innerHTML`, `outerHTML`, `insertAdjacentHTML` ani `document.write`.
- **Konfiguracja domyślnie bezpieczna.** Dane demo i dokumentacja API są domyślnie wyłączone, ciasteczko ma `Secure`, a seed wymaga `PATCHPOINT_DEMO_PASSWORD`, spełniającego politykę haseł (`backend/app/config.py`). API odmawia startu na bazie o innym schemacie (`PRAGMA user_version`) niż oczekiwany.
- **Logowanie zdarzeń.** Zdarzenia bezpieczeństwa to jedna linia JSON w loggerze `patchpoint.security` (`backend/app/audit.py`); nigdy nie zawierają haseł, tokenów ani hashy. Wszystkie zawierają `client_ip` (dla `demo_data_seeded` — `null`). `client_ip` to adres peera TCP (`request.client.host`): `make run` startuje uvicorna z `--no-proxy-headers`, więc nagłówek `X-Forwarded-For` nie wpływa na to pole (SEC-003); dowód: `backend/tests/test_client_ip.py` uruchamia prawdziwy serwer poleceniem z `make run`.

| Zdarzenie | Poziom | Pola (poza `client_ip`) |
|---|---|---|
| `user_registered` | INFO | `username`, `user_id`, `role` |
| `registration_conflict` | WARNING | `username` |
| `login_succeeded` | INFO | `username`, `user_id` |
| `login_failed` | WARNING | `username`, `reason` (`unknown_user` albo `bad_password`) |
| `login_blocked` | WARNING | `username` |
| `logout` | INFO | `user_id` (`null`, gdy brak aktywnej sesji) |
| `session_rejected` | WARNING | `reason` (`unknown`, `idle_timeout` albo `absolute_timeout`), `user_id` |
| `access_denied` | WARNING | `user_id`, `reason` (`agent_role_required` albo `not_ticket_owner`), `path`, `ticket_id` |
| `ticket_updated` | INFO | `user_id`, `ticket_id`, `status`, `priority`, `assignee_id` (niezmieniane pola: `null`) |
| `demo_data_seeded` | INFO | `users` |
| `validation_failed` | WARNING | `path`, `types` (typy błędów, np. `extra_forbidden`), `fields` (lokalizacje pól, np. `body.role`); nigdy wartości przesłanych pól; `client_ip` jest obecne jak w pozostałych zdarzeniach `patchpoint.security` |
| `internal_error` (logger `patchpoint.errors`, poziom ERROR, z tracebackiem) | ERROR | `error_id`, `method`, `path`, `exception`, `sql` (bez `client_ip`) |

## 7. Zmiany kontraktu API względem Fazy 1

| Obszar | Faza 1 | Faza 2 |
|---|---|---|
| Rejestracja | pole `role`, dowolne hasło, 409 ze szczegółami SQLite | 422 dla nieznanych pól, hasło 15–128 znaków bez loginu, login `[A-Za-z0-9._@+-]{3,50}`, 409 „Username is already taken” |
| Logowanie | 404 dla nieznanego loginu i 401 dla złego hasła, odpowiedź `{token, user}`, ciasteczko bez flag | 401 „Invalid username or password”, 429 z `Retry-After` po zbyt wielu próbach, odpowiedź `{user}`, ciasteczko `HttpOnly; Secure; SameSite=Strict` |
| Uwierzytelnianie | ciasteczko lub nagłówek `Bearer`, bez wygasania | tylko ciasteczko, wygasanie po 30 min bezczynności i po 8 h |
| Wylogowanie | tylko usunięcie ciasteczka | usunięcie sesji na serwerze i ciasteczka |
| `/api/auth/me` | z `password_hash` | bez `password_hash` |
| Health | wersje i ścieżka bazy | `{"status": "ok"}` |
| Lista zgłoszeń | bez limitu, SQL składany z `search` | `limit` (1–100, domyślnie 50) i `offset`, `search` do 100 znaków, zapytanie parametryzowane |
| Szczegóły i komentarze | cudze zgłoszenia dostępne, duży identyfikator daje 500, `comments` zawiera wszystkie komentarze | 404 dla cudzych zgłoszeń, 422 dla identyfikatorów poza zakresem 1…2⁶³−1; `comments` to najnowsze 50 komentarzy (od najstarszego do najnowszego), a nowe pole `comment_count` podaje liczbę wszystkich komentarzy zgłoszenia |
| Modele wejściowe | nieznane pola ignorowane, brak limitów | 422 dla nieznanych pól, limity długości pól, ciało powyżej 64 KiB daje 413 (tekst `Content Too Large`, nie JSON) |
| Błędy 500 | SQL, parametry, ścieżka i traceback w odpowiedzi | `{"detail": "Internal server error", "error_id": "<uuid>"}` |
| Dokumentacja API | publiczna (`/docs`, `/redoc`, `/openapi.json`) | domyślnie wyłączona (`PATCHPOINT_DOCS_ENABLED=true` ją włącza) |
| CORS | dowolny origin z poświadczeniami | lista originów z konfiguracji |
| Dane demo | domyślnie włączone, konto `admin` i znane hasła | na żądanie, z hasłem z `PATCHPOINT_DEMO_PASSWORD`, bez konta `admin` |

Bieżące endpointy (każdy może też dać 413 dla ciała powyżej 64 KiB i 500 `{"detail": "Internal server error", "error_id": "<uuid>"}`):

| Metoda | Ścieżka | Uwierzytelnienie | Rola | Opis | Kody odpowiedzi |
|---|---|---|---|---|---|
| GET | `/api/health` | nie | — | stan API: `{"status": "ok"}` | 200 |
| POST | `/api/auth/register` | nie | — | rejestracja konta z rolą `employee` (pola `username`, `password`, `full_name`, `department`) | 201, 409, 422 |
| POST | `/api/auth/login` | nie | — | logowanie: zwraca `{user}` i ustawia ciasteczko `session` (`HttpOnly; Secure; SameSite=Strict`) | 200, 401, 422, 429 |
| POST | `/api/auth/logout` | nie | — | usuwa sesję na serwerze i ciasteczko | 200 |
| GET | `/api/auth/me` | tak | dowolna | dane zalogowanego użytkownika | 200, 401 |
| POST | `/api/tickets` | tak | dowolna | utworzenie zgłoszenia | 201, 401, 422 |
| GET | `/api/tickets` | tak | dowolna | lista zgłoszeń z parametrami `status`, `search`, `limit` (1–100, domyślnie 50) i `offset`; pracownik widzi własne, agent wszystkie | 200, 401, 422 |
| GET | `/api/tickets/{ticket_id}` | tak | dowolna | szczegóły z najnowszymi 50 komentarzami i `comment_count`; cudze zgłoszenie pracownika daje 404 | 200, 401, 404, 422 |
| PATCH | `/api/tickets/{ticket_id}` | tak | `agent` | zmiana `status`, `priority`, `assignee_id` | 200, 400, 401, 403, 404, 422 |
| POST | `/api/tickets/{ticket_id}/comments` | tak | dowolna | dodanie komentarza do widocznego zgłoszenia | 201, 401, 404, 422 |

Kontrakt wygenerowany przez FastAPI: [`dowody/openapi.json`](dowody/openapi.json).

## 8. Weryfikacja

- Testy ([`dowody/testy.txt`](dowody/testy.txt)): 137 zaliczonych, 0 niezaliczonych; pokrycie `TOTAL` 98% (98,30%; próg 80%).
- Jakość ([`dowody/jakosc.txt`](dowody/jakosc.txt)): `make lint` (`ruff check` z regułami `S` i `ruff format --check`) — „All checks passed!” i „28 files already formatted”; `make typecheck` — „Success: no issues found in 28 source files”.
- Demo ([`dowody/demo.txt`](dowody/demo.txt)): przepływ end-to-end na kontach demo kończy się linią `DEMO ZAKOŃCZONE POWODZENIEM`.
- PoC na kodzie Fazy 1 ([`dowody/poc-faza-1.txt`](dowody/poc-faza-1.txt)): `Podsumowanie: podatne=22, naprawione=0, pominięte=0`, kod wyjścia 1.
- PoC na kodzie Fazy 2 ([`dowody/poc-faza-2.txt`](dowody/poc-faza-2.txt)): `Podsumowanie: podatne=0, naprawione=22, pominięte=0`, kod wyjścia 0.
- Zdarzenia bezpieczeństwa zarejestrowane podczas uruchomienia ([`dowody/zdarzenia-bezpieczenstwa.txt`](dowody/zdarzenia-bezpieczenstwa.txt)), np.:

```text
2026-11-18 16:25:04,814 INFO patchpoint.security {"client_ip": "127.0.0.1", "event": "login_succeeded", "user_id": 2, "username": "jan.kowalski"}
2026-11-18 16:24:56,531 WARNING patchpoint.security {"client_ip": "127.0.0.1", "event": "access_denied", "path": "/api/tickets/4", "reason": "not_ticket_owner", "ticket_id": 4, "user_id": 5}
2026-11-18 16:24:56,657 WARNING patchpoint.security {"client_ip": "127.0.0.1", "event": "login_failed", "reason": "unknown_user", "username": "poc.nobody.afb5b8e2"}
```

QA i końcowy code review działają po tym dokumencie, w procesie delivery; ich raporty trafiają do `docs/testing/reports/` i `docs/reviews/`.

## 9. Ryzyka rezydualne i przekazanie do Fazy 3

- **TLS i HSTS.** Lokalnie aplikacja działa po HTTP; atrybut `Secure` ciasteczka działa na `localhost` i `*.localhost`, ale na rzeczywistym środowisku potrzebne są TLS i HSTS.
- **Nagłówki frontendu.** CSP jest w znaczniku `<meta>`; `frame-ancestors` i pozostałe nagłówki ochronne musi ustawiać serwer statyczny, bo `python -m http.server` ich nie dodaje.
- **Jedna witryna dla UI i API.** Ciasteczko ma `SameSite=Strict`, więc UI i API muszą działać w obrębie jednej witryny; `SameSite=None` wymagałoby osobnej ochrony przed CSRF.
- **Sekrety.** `PATCHPOINT_DEMO_PASSWORD` i inne sekrety powinny pochodzić z menedżera sekretów chmury, nie ze zmiennych wpisywanych ręcznie.
- **Limit prób per IP.** Obecny limit działa per konto, więc napastnik może zablokować cudze konto na 15 minut; limit per IP i ochrona przed password spraying należą do brzegu sieci (WAF, API gateway).
- **Enumeracja loginów przez rejestrację.** Odpowiedź 409 „Username is already taken” ujawnia zajęte loginy; ryzyko zaakceptowane.
- **Polityka haseł.** Brak listy haseł popularnych i wyciekłych.
- **Zbieranie logów.** Zdarzenia `patchpoint.security` trafiają na stderr; zbieranie, retencja i alertowanie to zadanie dla Fazy 3.
- **Źródło `client_ip` za reverse proxy (SEC-003).** Uvicorn domyślnie ufa nagłówkom proxy od `127.0.0.1` i `::1`, dlatego `make run` ma `--no-proxy-headers`. Gdy Faza 3 doda reverse proxy, uruchom uvicorna z `--forwarded-allow-ips` ustawionym wyłącznie na adres proxy (bez `--no-proxy-headers`) i dostosuj `backend/tests/test_client_ip.py`; inaczej `client_ip` pokaże adres proxy albo da się go podrobić.
- **Zależności i obraz (A03).** Skanowanie zależności i obrazu kontenera (Semgrep, Trivy w CI) pozostaje do wykonania w Fazie 3.
- **Migracja schematu.** Przy innej wersji `user_version` API odmawia startu; procedura migracji danych nie istnieje.
- **Konta agentów.** Konta agentów powstają wyłącznie przez seed demo; brak procesu zakładania ich w środowisku docelowym.
- **Safari.** Lokalnie wymaga `PATCHPOINT_COOKIE_SECURE=false`, bo nie przyjmuje `Secure` na `http://patchpoint.localhost`.
- **Ciasteczko sesji nie jest izolowane portem (SEC-001).** Przeglądarki wysyłają ciasteczko hosta na każdy port (RFC 6265 §8.5), a inny port tego samego hosta to ta sama witryna, więc ani `SameSite=Strict`, ani lista CORS, ani `HttpOnly` nie chronią przed obcą aplikacją na tym hoście (lista CORS dotyczy odczytu odpowiedzi przez przeglądarkę, nie samego ciasteczka). Lokalnie UI i API działają pod `patchpoint.localhost` (osobna witryna od `localhost`), więc aplikacje na `localhost:<port>` ciasteczka nie dostają; aplikacja uruchomiona pod `patchpoint.localhost:<port>` nadal by je dostała. W Fazie 3: dedykowany origin HTTPS, prefiks `__Host-` i UI z API pod jednym originem za reverse proxy. Skuteczność w przeglądarce nie była testowana. Szczegóły: scenariusz CORS-2 w [`threat-model.md`](threat-model.md).
- **Hashowanie Argon2 poza pętlą zdarzeń (PERF-001).** `register` i `login` wykonują wyłącznie czyste funkcje Argon2 (`hash_password`, `verify_password`, `simulate_password_check`) w puli wątków (`run_in_threadpool`), więc pętla zdarzeń nie blokuje się na czas hashowania; połączenie SQLite pozostaje w wątku pętli. Nie zmienia to kosztu: anonimowy klient nadal może wywołać dowolnie dużo pracy Argon2 (rejestracja, logowanie na zmieniające się loginy), a równoległe hashowanie jest ograniczone tylko domyślną pulą wątków Starlette (40 wątków), co przy 64 MiB na hash daje szczyt pamięci rzędu 2,5 GiB [wniosek, nie pomiar]. Limit żądań per IP, przepustowość i limity zasobów procesu należą do brzegu sieci w Fazie 3. Dokładność blokady konta wynika z tego, że sprawdzenie i zapis próby nie przedzielają się `await`, więc obowiązuje w obrębie jednego procesu uvicorna; przy wielu workerach potrzebny byłby atomowy zapis w bazie.
- **Luki w testach zdarzeń.** Żaden test nie sprawdza zdarzeń `login_blocked`, `login_failed` z powodem `unknown_user` ani `logout` (zdarzenia widać w [`dowody/zdarzenia-bezpieczenstwa.txt`](dowody/zdarzenia-bezpieczenstwa.txt)).
