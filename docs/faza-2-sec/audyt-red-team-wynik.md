# Raport SAST: PatchPoint (`backend/app/`, `frontend/`, commit `ab08633`)

Analiza była wyłącznie statyczna. Aplikacji, testów ani narzędzi nie uruchamiałem. Kod sprawdziłem pod kątem OWASP Top 10:2025: A01 Broken Access Control, A02 Security Misconfiguration, A03 Software Supply Chain Failures, A04 Cryptographic Failures, A05 Injection, A06 Insecure Design, A07 Authentication Failures, A08 Software or Data Integrity Failures, A09 Security Logging & Alerting Failures, A10 Mishandling of Exceptional Conditions.

## 1. Tabela zbiorcza

| ID | Tytuł | OWASP Top 10:2025 | CWE | Lokalizacja | Ważność | Pewność |
|---|---|---|---|---|---|---|
| RT-01 | SQL Injection w parametrze `search` listy zgłoszeń | A05 (pomoc.: A01) | CWE-89 | `backend/app/routers/tickets.py:86,89` `list_tickets` | krytyczna | wysoka |
| RT-02 | Samodzielna rejestracja z rolą `agent` (mass assignment) | A01 (pomoc.: A06) | CWE-915, CWE-269 | `backend/app/schemas.py:17`, `backend/app/routers/auth.py:20-28` `register` | krytyczna | wysoka |
| RT-03 | Przewidywalny token sesji: `md5(username:timestamp)` | A07 (pomoc.: A04) | CWE-330, CWE-340 | `backend/app/security.py:16-17` `generate_session_token` | krytyczna | wysoka |
| RT-04 | Brak kontroli dostępu do obiektu przy odczycie zgłoszenia i dodawaniu komentarza (IDOR) | A01 | CWE-639, CWE-862 | `backend/app/routers/tickets.py:94-105` `get_ticket`, `:158-178` `add_comment` | wysoka | wysoka |
| RT-05 | Stored XSS: dane z API wstawiane przez `innerHTML` | A05 | CWE-79 | `frontend/app.js:100,110-122,174-201` | wysoka | wysoka |
| RT-06 | CORS: `allow_origins=["*"]` razem z `allow_credentials=True` | A02 (pomoc.: A01) | CWE-942, CWE-346 | `backend/app/main.py:26-32` `create_app` | wysoka | średnia |
| RT-07 | Słabe zarządzanie cyklem życia sesji: brak wygaśnięcia, wylogowanie nie unieważnia sesji, cookie bez flag | A07 | CWE-613, CWE-1004, CWE-614 | `backend/app/routers/auth.py:58,60,64-66`, `backend/app/schema.sql:11-15` | wysoka | wysoka |
| RT-08 | Hasła haszowane MD5 bez soli | A04 | CWE-916, CWE-759, CWE-328 | `backend/app/security.py:8-13` `hash_password` | wysoka | wysoka |
| RT-09 | Domyślne konta demo ze znanymi hasłami i brak polityki haseł | A07 (pomoc.: A02) | CWE-1392, CWE-798, CWE-521 | `backend/app/database.py:13-18`, `backend/app/config.py:14`, `backend/app/schemas.py:14`, `frontend/index.html:52` | wysoka | wysoka |
| RT-10 | Gadatliwe błędy bazy danych (SQL, parametry, ścieżka, traceback) | A10 (pomoc.: A02) | CWE-209, CWE-497 | `backend/app/main.py:34-46`, `backend/app/database.py:21-27`, `backend/app/routers/auth.py:31-34` | średnia | wysoka |
| RT-11 | `password_hash` zwracany w odpowiedziach API | A01 (pomoc.: A04) | CWE-200, CWE-522 | `backend/app/schemas.py:27`; `routers/auth.py:42,60,70-71` | średnia | wysoka |
| RT-12 | Enumeracja kont i brak ochrony przed brute force | A07 | CWE-204, CWE-307 | `backend/app/routers/auth.py:46-50,31-34` | średnia | wysoka |
| RT-13 | Tryb `debug=True`: traceback przy nieobsłużonych wyjątkach i publiczne `/docs` | A02 (pomoc.: A10) | CWE-489, CWE-209 | `backend/app/main.py:23` | średnia | średnia |
| RT-14 | Nieuwierzytelniony `/api/health` ujawnia ścieżkę bazy i wersje | A02 | CWE-497 | `backend/app/routers/health.py:13-23` | niska | wysoka |
| RT-15 | Brak logowania zdarzeń bezpieczeństwa i audytu zmian | A09 | CWE-778 | cały `backend/app/` (np. `routers/auth.py:45-60`, `routers/tickets.py:108-155`) | niska | wysoka |
| RT-16 | Brak CSP i nagłówków bezpieczeństwa, komunikacja po HTTP | A02 | CWE-693, CWE-1021, CWE-319 | `frontend/index.html:3-9`, `frontend/app.js:1`, `backend/app/main.py:23-32` | niska | średnia |

## 2. Szczegóły

### RT-01 — SQL Injection w parametrze `search` listy zgłoszeń
- **OWASP / CWE:** A05:2025 Injection (pomocniczo A01: obejście filtra wierszy), CWE-89.
- **Lokalizacja:** `backend/app/routers/tickets.py:86` (budowa warunku), `:89` (wykonanie), funkcja `list_tickets` (`GET /api/tickets`).
- **Błąd:** `search` (dowolny tekst z query string) trafia przez f-string prosto do zapytania: `f"(t.title LIKE '%{search}%' OR t.description LIKE '%{search}%')"`. Potem `fetch_all(conn, f"{TICKET_SELECT}{where} ORDER BY t.id DESC")` wykonuje je bez parametrów. Ten sam f-string mają `status` (`:84`) i `user.id` (`:82`), ale tam typy są zawężone przez `TicketStatus` i `int`, więc obecnie nie da się ich wykorzystać.
- **Nadużycie:** zalogowany pracownik wpisuje w `search` fragment, który zamyka literał i nawias, a potem dokleja `OR` albo `UNION SELECT`. Komentarz SQL wycina resztę zapytania. W ten sposób omija warunek `t.reporter_id = …` i może odczytać dowolne tabele, np. `sessions.token` i `users.password_hash`, podstawione w kolumny zwracane jako „zgłoszenia”.
- **Wpływ:** odczyt całej bazy, w tym aktywnych tokenów sesji agentów (przejęcie konta, por. RT-07) i hashy haseł (por. RT-08). `sqlite3` wykonuje jedną instrukcję na wywołanie, więc ta ścieżka nie pozwala na dopisane instrukcje modyfikujące dane. Ryzyko dotyczy głównie poufności, a przez przejęcie sesji pośrednio integralności.
- **Ważność:** krytyczna. Wystarczy dowolne konto pracownika (samodzielna rejestracja), a skutkiem jest zrzut sekretów uwierzytelniających. **Pewność:** wysoka.
- **Naprawa:** w `list_tickets` używać wyłącznie placeholderów, np. `conditions.append("(t.title LIKE ? OR t.description LIKE ?)")` i `params += [f"%{search}%"] * 2`, i przekazać `params` do `fetch_all`. To samo zrobić dla `status` i `reporter_id`. Rozważyć escapowanie `%`/`_` z `ESCAPE` oraz limit długości `search`.

### RT-02 — Samodzielna rejestracja z rolą `agent` (mass assignment)
- **OWASP / CWE:** A01:2025 (pomocniczo A06 Insecure Design), CWE-915, CWE-269.
- **Lokalizacja:** `backend/app/schemas.py:17` (`role: Role = Role.EMPLOYEE` w `UserCreate`), `backend/app/routers/auth.py:20-28` (`register` przekazuje `role=payload.role`).
- **Błąd:** publiczny endpoint `POST /api/auth/register` przyjmuje od klienta pole `role` i zapisuje je bez żadnej autoryzacji. Frontend tego pola nie wysyła, ale API je akceptuje.
- **Nadużycie:** nieuwierzytelniony użytkownik wysyła rejestrację z `"role": "agent"` i od razu loguje się jako agent Helpdesku. Schemat OpenAPI z `/docs` (RT-13) pokazuje, że takie pole istnieje.
- **Wpływ:** pełna eskalacja uprawnień: wgląd we wszystkie zgłoszenia, zmiana statusów i przypisań.
- **Ważność:** krytyczna. Atak jest trywialny, nie wymaga konta i daje najwyższą rolę. **Pewność:** wysoka.
- **Naprawa:** usunąć `role` z `UserCreate`. W `register` zawsze zapisywać `Role.EMPLOYEE`. Nadawanie roli `agent` przenieść do osobnego endpointu chronionego `require_agent` albo do procesu administracyjnego. Rozważyć `model_config = ConfigDict(extra="forbid")` w modelach wejściowych.

### RT-03 — Przewidywalny token sesji
- **OWASP / CWE:** A07:2025 (pomocniczo A04: MD5 jako „generator”), CWE-330, CWE-340.
- **Lokalizacja:** `backend/app/security.py:16-17` `generate_session_token`; użycie w `backend/app/routers/auth.py:52-57`; akceptacja tokenu z nagłówka `Authorization: Bearer` w `backend/app/dependencies.py:33-37`.
- **Błąd:** token to `md5(f"{username}:{int(time.time())}")`. Nie ma w nim żadnej losowości, a jedyną zmienną jest sekunda logowania. `INSERT OR IGNORE` (`auth.py:55`) sprawia, że dwa logowania tego samego użytkownika w tej samej sekundzie dostają ten sam token.
- **Nadużycie:** napastnik zna login (konta demo z RT-09, enumeracja z RT-12) i przybliżony czas logowania ofiary, np. ze znaczników `updated_at` zgłoszeń. Generuje lokalnie kandydatów z kolejnych sekund i sprawdza je nagłówkiem `Bearer` na `/api/auth/me`. Sesje nie wygasają (RT-07), a prób nikt nie ogranicza (RT-12), więc nawet przeszukanie wielu dni (86 400 kandydatów na dobę) jest wykonalne. Cookie i CORS nie są tu do niczego potrzebne.
- **Wpływ:** przejęcie sesji dowolnego użytkownika, w tym agenta, bez znajomości hasła.
- **Ważność:** krytyczna. Atak jest zdalny i nie wymaga konta. **Pewność:** wysoka.
- **Naprawa:** `secrets.token_urlsafe(32)` w `generate_session_token`, bez parametru `username`. W bazie przechowywać tylko skrót tokenu (np. SHA-256) i porównywać po skrócie. Zamiast `INSERT OR IGNORE` używać zwykłego `INSERT`.

### RT-04 — IDOR: odczyt cudzego zgłoszenia i komentowanie cudzych zgłoszeń
- **OWASP / CWE:** A01:2025, CWE-639, CWE-862.
- **Lokalizacja:** `backend/app/routers/tickets.py:94-105` `get_ticket` (`dependencies=[Depends(get_current_user)]`, handler nie dostaje obiektu użytkownika); `:158-178` `add_comment` (sprawdza tylko, czy zgłoszenie istnieje, `:162-164`).
- **Błąd:** oba endpointy wymagają jedynie uwierzytelnienia. Nie sprawdzają, czy pracownik jest zgłaszającym (`reporter_id`). Filtr własności istnieje tylko w `list_tickets` (`:81-82`).
- **Nadużycie:** pracownik iteruje po sekwencyjnych `ticket_id` w `GET /api/tickets/{id}` i czyta cudze zgłoszenia razem z komentarzami. Przez `POST /api/tickets/{id}/comments` może też dopisywać komentarze do dowolnego zgłoszenia, w tym ładunki XSS (RT-05).
- **Wpływ:** ujawnienie danych innych pracowników (opisy, lokalizacje, numery inwentarzowe, odpowiedzi Helpdesku) i naruszenie integralności wątków.
- **Ważność:** wysoka. Wyciek dotyczy wszystkich zgłoszeń, a do ataku wystarczy konto pracownika. **Pewność:** wysoka.
- **Naprawa:** w obu handlerach przyjmować `user: CurrentUser`. Dla `Role.EMPLOYEE` dodać do zapytania warunek `t.reporter_id = ?` i zwracać 404, gdy brak dopasowania. Najlepiej wydzielić jedną funkcję `get_ticket_for_user(conn, ticket_id, user)` i używać jej w obu miejscach.

### RT-05 — Stored XSS we frontendzie
- **OWASP / CWE:** A05:2025 Injection, CWE-79.
- **Lokalizacja:** `frontend/app.js:100` (`userInfo.innerHTML` z `full_name`), `:110-122` `renderTickets` (`title` `:115`, `reporter_name` `:119`, `assignee_name` `:120`), `:174-201` `openTicket` (`author_name` `:176`, `body` `:178`, `title` `:184`, `asset_tag` `:189`, `location` `:190`, `reporter_name` `:193`, `assignee_name` `:194`, `description` `:198`).
- **Błąd:** pola tekstowe sterowane przez użytkownika trafiają do szablonów i do `innerHTML` bez kodowania HTML. Backend przyjmuje te pola bez ograniczeń (`TicketCreate`, `UserCreate.full_name`, `CommentCreate.body`).
- **Nadużycie:** pracownik tworzy zgłoszenie (albo rejestruje się z `full_name`) zawierające znacznik HTML z handlerem zdarzenia. Gdy agent otworzy listę, skrypt wykona się na originie `http://localhost:5500`. Stamtąd może wołać API z poświadczeniami agenta (`credentials: "include"`). Może też odczytać `document.cookie`: cookie `session` nie ma `HttpOnly` (RT-07), a cookies nie są izolowane po porcie, więc cookie ustawione dla `localhost` jest widoczne także z portu 5500.
- **Wpływ:** przejęcie sesji agenta i wykonywanie akcji w jego imieniu, a do tego odczyt `password_hash` z `currentUser` (RT-11).
- **Ważność:** wysoka. Atak jest trwały (stored), wymierzony w rolę uprzywilejowaną i dostępny dla każdego pracownika. **Pewność:** wysoka.
- **Naprawa:** budować DOM przez `document.createElement` i `textContent`, albo przepuszczać każdą wartość przez funkcję `escapeHtml()` przed interpolacją. Wartości enumów mapować przez słowniki bez fallbacku do surowej wartości. Dodatkowo CSP (RT-16) i `HttpOnly` (RT-07).

### RT-06 — CORS z wildcardem i poświadczeniami
- **OWASP / CWE:** A02:2025 (pomocniczo A01), CWE-942, CWE-346.
- **Lokalizacja:** `backend/app/main.py:26-32` (`allow_origins=["*"]`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`).
- **Błąd:** przeglądarka nie zaakceptuje dosłownego `*` przy poświadczeniach. Starlette `CORSMiddleware` w takiej konfiguracji odpowiada więc echem nagłówka `Origin` (w preflight i przy żądaniach z cookie) i dodaje `Access-Control-Allow-Credentials: true`. Efekt: każdy origin jest traktowany jako zaufany. `[INFERENCE]` To opis znanego zachowania Starlette; zainstalowanej wersji nie weryfikowałem, bo pliki zależności są poza zakresem.
- **Nadużycie:** strona na dowolnym originie, z którego przeglądarka wyśle cookie `session`, może czytać odpowiedzi API ofiary (`/api/auth/me` z hashem, `/api/tickets`) i wykonywać `POST`/`PATCH`. Domyślne `SameSite=Lax` z `set_cookie` w Starlette blokuje cookie dla stron cross-site. Atak działa jednak z każdej innej aplikacji na `http://localhost:<port>` (ten sam site) i stanie się w pełni zdalny, jeśli zespół ustawi `SameSite=None`, żeby obsłużyć frontend w innej domenie.
- **Wpływ:** odczyt danych i działania w imieniu zalogowanego użytkownika (CSRF z odczytem odpowiedzi).
- **Ważność:** wysoka. Wyłącza politykę same-origin dla API z poświadczeniami. **Pewność:** średnia. Realna eksploatowalność zależy od polityki cookies przeglądarki i wersji Starlette, czego statycznie nie da się potwierdzić.
- **Naprawa:** w `create_app` ustawić `allow_origins=["http://localhost:5500"]` (z konfiguracji `Settings`), `allow_methods=["GET","POST","PATCH"]`, `allow_headers=["Content-Type","Authorization"]`. Cookie z jawnym `samesite="strict"` lub `"lax"` (RT-07).

### RT-07 — Słabe zarządzanie cyklem życia sesji
- **OWASP / CWE:** A07:2025, CWE-613, CWE-1004, CWE-614.
- **Lokalizacja:** `backend/app/routers/auth.py:58` (`set_cookie(key=…, value=token)` bez flag), `:60` (token w treści `LoginResponse`), `:64-66` `logout` (tylko `delete_cookie`); `backend/app/schema.sql:11-15` (tabela `sessions` bez `expires_at`); `backend/app/dependencies.py:42-48` (brak kontroli wieku sesji).
- **Błąd:** sesje nigdy nie wygasają. Wylogowanie usuwa cookie w przeglądarce, ale nie usuwa wiersza w `sessions`. Cookie nie ma `HttpOnly`, `Secure` ani jawnego `SameSite`/`Max-Age`. Token jest też zwracany w JSON, choć frontend go nie używa.
- **Nadużycie:** token raz zdobyty przez XSS (RT-05), SQLi (RT-01) albo zgadnięcie (RT-03) działa bezterminowo, także po wylogowaniu ofiary. Można go podać w nagłówku `Bearer` z dowolnego miejsca.
- **Wpływ:** trwałe przejęcie konta. Użytkownik nie ma jak unieważnić skradzionej sesji.
- **Ważność:** wysoka. Wzmacnia wszystkie scenariusze kradzieży sesji. **Pewność:** wysoka.
- **Naprawa:** dodać `expires_at` (i ewentualnie `last_seen_at`) do `sessions` i sprawdzać ją w `get_current_user`. `logout` powinien przyjmować token i wykonywać `DELETE FROM sessions WHERE token = ?`. `set_cookie(..., httponly=True, secure=True, samesite="strict", max_age=…)`. Usunąć `token` z `LoginResponse`, chyba że klienci Bearer są świadomie wspierani.

### RT-08 — MD5 bez soli do haszowania haseł
- **OWASP / CWE:** A04:2025 Cryptographic Failures, CWE-916, CWE-759, CWE-328.
- **Lokalizacja:** `backend/app/security.py:8-13` `hash_password` / `verify_password`.
- **Błąd:** `hashlib.md5(password)` to szybki skrót bez soli. Te same hasła dają te same hashe (np. `jan.kowalski` i `anna.nowak`, oba `password123`). Porównanie `==` nie działa w stałym czasie.
- **Nadużycie:** hash zdobyty przez RT-01, RT-05/RT-06 lub RT-11 można odwrócić tablicami tęczowymi albo słownikiem praktycznie od ręki.
- **Wpływ:** odzyskanie haseł w jawnej postaci, także do innych systemów, jeśli użytkownicy powtarzają hasła.
- **Ważność:** wysoka. W tej aplikacji hashe łatwo wyciekają (kilka niezależnych ścieżek). **Pewność:** wysoka.
- **Naprawa:** Argon2id (`argon2-cffi`) albo bcrypt/scrypt z solą w `hash_password`/`verify_password`, weryfikacja funkcją biblioteki (stały czas). Migracja: przy następnym udanym logowaniu przehaszować hasło.

### RT-09 — Domyślne konta demo i brak polityki haseł
- **OWASP / CWE:** A07:2025 (pomocniczo A02), CWE-1392, CWE-798, CWE-521.
- **Lokalizacja:** `backend/app/database.py:13-18` (`DEMO_USERS`: `admin/admin123` i `helpdesk/helpdesk123` z rolą `agent`); `backend/app/config.py:14` (`seed_demo_data: bool = True`); `backend/app/main.py:20` (seed w `lifespan`); `backend/app/schemas.py:14` (`password: str` bez ograniczeń); `frontend/index.html:52` (pole hasła bez `required`).
- **Błąd:** domyślnie, bez ustawionej zmiennej `PATCHPOINT_SEED_DEMO_DATA`, przy pustej bazie powstają konta agentów z hasłami zapisanymi w kodzie. Rejestracja przyjmuje dowolne hasło, także puste.
- **Nadużycie:** napastnik loguje się jako `admin` znanym hasłem, albo zgaduje słabe hasła zarejestrowanych użytkowników (bez limitów, RT-12).
- **Wpływ:** natychmiastowy dostęp na poziomie agenta i przejmowanie kont ze słabymi hasłami.
- **Ważność:** wysoka. Seed jest włączony domyślnie, a konta mają najwyższą rolę. **Pewność:** wysoka, z zastrzeżeniem, że konfiguracja środowiska spoza zakresu może wyłączać seed.
- **Naprawa:** `seed_demo_data: bool = False` jako bezpieczny default. Hasła demo generować losowo przy seedzie albo pobierać z env. W `UserCreate.password` dodać `Field(min_length=12, max_length=128)` plus ewentualnie sprawdzanie haseł z listy popularnych. We frontendzie dodać `required minlength`.

### RT-10 — Gadatliwe błędy bazy danych
- **OWASP / CWE:** A10:2025 Mishandling of Exceptional Conditions (pomocniczo A02), CWE-209, CWE-497.
- **Lokalizacja:** `backend/app/main.py:34-46` `database_error_handler` (zwraca `message`, `query`, `params`, `database`, `traceback`); `backend/app/database.py:21-27` (`DatabaseError` niesie SQL i parametry); `backend/app/routers/auth.py:31-34` (409 z `exc.original`, np. „UNIQUE constraint failed: users.username”); `frontend/app.js:67` (frontend wyświetla `JSON.stringify(body)` użytkownikowi).
- **Błąd:** każdy wyjątek `sqlite3.Error` trafia do klienta jako pełne zapytanie SQL z nazwami tabel i kolumn, parametry, komunikat silnika, absolutna ścieżka pliku bazy i stack trace ze ścieżkami kodu. CORS (RT-06) dokłada nagłówki także do tych odpowiedzi.
- **Nadużycie:** wystarczy wpisać apostrof w `search` (RT-01), żeby dostać kompletny `TICKET_SELECT` z JOIN-ami. To podaje gotową strukturę do dopasowania `UNION`. Błąd w zapytaniu sesji ujawnia też `params` (token), a w `create_user` hash hasła.
- **Wpływ:** ujawnienie architektury bazy i serwera, wyraźne ułatwienie RT-01.
- **Ważność:** średnia. Samo w sobie nie daje dostępu do danych, ale skraca drogę do ataku krytycznego. **Pewność:** wysoka.
- **Naprawa:** handler w `main.py` ma zwracać ogólny komunikat 500 z identyfikatorem korelacji (`{"error": "internal_error", "id": "<uuid>"}`), a szczegóły (SQL bez wrażliwych parametrów) zapisywać tylko w logu serwera (RT-15). W `register` zwracać stały komunikat 409 bez treści wyjątku SQLite.

### RT-11 — `password_hash` w odpowiedziach API
- **OWASP / CWE:** A01:2025 (pomocniczo A04), CWE-200, CWE-522.
- **Lokalizacja:** `backend/app/schemas.py:27` (`UserResponse.password_hash`); zwracane w `backend/app/routers/auth.py:42` (`register`), `:60` (`login`), `:70-71` (`get_me`); trzymane w `currentUser` we `frontend/app.js:279` (login) i `:346` (`init`).
- **Błąd:** model odpowiedzi współdzielony z mapowaniem wiersza `users` (`SELECT u.*` / `SELECT *`) wystawia skrót hasła klientowi.
- **Nadużycie:** każdy kanał, który czyta odpowiedzi API lub pamięć strony (XSS z RT-05, CORS z RT-06, logi proxy, historia DevTools), dostaje hash MD5, który łatwo odwrócić (RT-08).
- **Wpływ:** wyciek poświadczeń.
- **Ważność:** średnia. Sam użytkownik widzi tylko własny hash, ale w łańcuchu z RT-05/RT-06/RT-08 daje hasło w jawnej postaci. **Pewność:** wysoka.
- **Naprawa:** usunąć `password_hash` z `UserResponse`. Do wewnętrznego wiersza z hashem używać osobnego modelu (np. `UserRecord`). W `get_current_user` i `login` wybierać jawne kolumny zamiast `u.*`/`*`.

### RT-12 — Enumeracja kont i brak ochrony przed brute force
- **OWASP / CWE:** A07:2025, CWE-204, CWE-307.
- **Lokalizacja:** `backend/app/routers/auth.py:46-50` `login` (404 „User '…' does not exist” wobec 401 „Invalid password”); `:31-34` `register` (409 dla istniejącego loginu); brak jakiegokolwiek limitu prób w `backend/app/`.
- **Błąd:** odpowiedzi odróżniają nieistniejący login od złego hasła. Nie ma rate limitingu, blokady konta ani opóźnień, ani dla `/login`, ani dla tokenów `Bearer` (`dependencies.py:32-48`).
- **Nadużycie:** napastnik najpierw ustala istniejące loginy (zwłaszcza agentów), a potem bez ograniczeń zgaduje hasła (RT-09) albo tokeny (RT-03).
- **Wpływ:** ułatwione przejęcie kont.
- **Ważność:** średnia. To wzmacniacz, nie samodzielna kompromitacja. **Pewność:** wysoka.
- **Naprawa:** jednolita odpowiedź 401 „Invalid credentials” dla obu przypadków (z wykonaniem weryfikacji hasła także dla nieistniejącego użytkownika, żeby wyrównać czas). Limit prób na IP i konto, np. middleware lub `slowapi` na `/api/auth/login` i dla nieudanych tokenów w `get_current_user`.

### RT-13 — Tryb `debug=True` i publiczna dokumentacja API
- **OWASP / CWE:** A02:2025 (pomocniczo A10), CWE-489, CWE-209.
- **Lokalizacja:** `backend/app/main.py:23` (`FastAPI(..., debug=True, ...)`, bez wyłączenia `docs_url`/`openapi_url`).
- **Błąd:** w trybie debug Starlette zwraca pełny traceback ze ścieżkami i fragmentami kodu dla każdego wyjątku, który nie jest `DatabaseError` ani `HTTPException`. `/docs` i `/openapi.json` są dostępne bez uwierzytelnienia.
- **Nadużycie:** zalogowany użytkownik podaje `ticket_id` lub `assignee_id` większe niż 64 bity. `[INFERENCE]` `sqlite3` rzuca wtedy `OverflowError`, który nie dziedziczy po `sqlite3.Error`, więc nie jest opakowany w `DatabaseError`. Podobnie wiersze wstrzyknięte przez RT-01, które nie przejdą walidacji `TicketResponse`. W obu przypadkach odpowiedzią jest traceback. Schemat OpenAPI ujawnia pole `role` w `UserCreate` (RT-02).
- **Wpływ:** ujawnienie kodu, ścieżek i struktury aplikacji oraz rekonesans całej powierzchni API.
- **Ważność:** średnia. **Pewność:** średnia. Konkretne wyzwalacze wynikają z zachowania bibliotek w czasie wykonania, którego nie weryfikowałem uruchomieniem.
- **Naprawa:** `debug` sterowany z `Settings` z domyślnym `False`. Ogólny handler `Exception` z bezpieczną odpowiedzią 500. `docs_url=None, redoc_url=None, openapi_url=None` poza środowiskiem deweloperskim. Ograniczenie zakresu `ticket_id` (`Path(ge=1, le=2**63-1)`).

### RT-14 — `/api/health` ujawnia szczegóły środowiska
- **OWASP / CWE:** A02:2025, CWE-497.
- **Lokalizacja:** `backend/app/routers/health.py:13-23` `health` (bez zależności uwierzytelniającej).
- **Błąd:** endpoint zwraca każdemu absolutną ścieżkę pliku bazy (`database_path.resolve()`), wersję SQLite, wersję Pythona i wersję aplikacji.
- **Nadużycie:** nieuwierzytelniony rekonesans: dopasowanie znanych podatności do wersji i poznanie układu katalogów serwera.
- **Wpływ:** ujawnienie informacji, które ułatwiają dalsze ataki.
- **Ważność:** niska. **Pewność:** wysoka.
- **Naprawa:** publiczny health check ma zwracać tylko `{"status": "ok"}`. Szczegóły diagnostyczne przenieść za `require_agent` albo do logów.

### RT-15 — Brak logowania zdarzeń bezpieczeństwa i audytu
- **OWASP / CWE:** A09:2025, CWE-778.
- **Lokalizacja:** cały `backend/app/`: brak `logging` (grep nie zwrócił wyników). Między innymi `routers/auth.py:45-60` (nieudane logowania), `:20-42` (rejestracje, także z `role=agent`), `routers/tickets.py:108-155` (`update_ticket` nawet nie pobiera użytkownika, więc nie wiadomo, który agent zmienił status).
- **Błąd:** nie są rejestrowane nieudane logowania, odmowy 403, błędy SQL ani zmiany statusów i przypisań.
- **Nadużycie:** brute force (RT-12), zgadywanie tokenów (RT-03), SQLi (RT-01) i samoeskalacja (RT-02) nie zostawiają śladu, który pozwoliłby wykryć atak lub go odtworzyć.
- **Wpływ:** brak wykrywalności i rozliczalności.
- **Ważność:** niska. Nie jest bezpośrednio eksploatowalne, ale wydłuża czas działania napastnika. **Pewność:** wysoka dla kodu w zakresie. Logi dostępowe serwera ASGI, jeśli istnieją, nie zastępują zdarzeń domenowych.
- **Naprawa:** moduł `logging` z logami strukturalnymi dla zdarzeń auth (sukces, porażka, wylogowanie), 401/403, błędów DB (szczegóły tylko w logu, RT-10) i zmian zgłoszeń. W `update_ticket` przyjmować `AgentUser` i zapisywać audyt (kto, co, kiedy). Bez haseł i tokenów w logach.

### RT-16 — Brak CSP i nagłówków bezpieczeństwa, komunikacja po HTTP
- **OWASP / CWE:** A02:2025, CWE-693, CWE-1021, CWE-319.
- **Lokalizacja:** `frontend/index.html:3-9` (brak `Content-Security-Policy`); `frontend/app.js:1` (`API_BASE_URL = "http://localhost:8000"`); `backend/app/main.py:23-32` (brak middleware nagłówków bezpieczeństwa).
- **Błąd:** nic nie ogranicza wykonywania skryptów inline ani handlerów zdarzeń, więc przy RT-05 nie ma drugiej linii obrony. Brak `X-Content-Type-Options`, `frame-ancestors`/`X-Frame-Options` i HTTPS.
- **Nadużycie:** ładunki XSS z RT-05 wykonują się bez przeszkód. Wdrożenie poza localhost przesyłałoby tokeny otwartym tekstem.
- **Wpływ:** brak mitigacji ograniczających skutki innych luk.
- **Ważność:** niska, bo aplikacja działa lokalnie. **Pewność:** średnia: serwer statyczny frontendu jest poza zakresem i może ustawiać nagłówki sam.
- **Naprawa:** w `index.html` dodać `<meta http-equiv="Content-Security-Policy" content="default-src 'self'; connect-src http://localhost:8000; script-src 'self'; object-src 'none'; base-uri 'none'">` (najlepiej jako nagłówek serwera). W backendzie middleware z `X-Content-Type-Options: nosniff` i `Content-Security-Policy: frame-ancestors 'none'`. TLS przy jakimkolwiek wdrożeniu poza localhost.

## 3. Powiązania między lukami

1. **Pracownik staje się agentem bez żadnego łańcucha:** RT-02 wystarcza sam. Ujawnienie pola `role` w `/docs` (RT-13) czyni go łatwym do odkrycia, a brak audytu (RT-15) ukrywa nadużycie.
2. **Zrzut sekretów przez SQLi:** RT-01 + RT-10 (pełne zapytanie SQL w odpowiedzi błędu ułatwia dopasowanie `UNION`) + RT-13 (traceback). Wynik:
   - tokeny z `sessions`, ważne bezterminowo i używalne przez `Bearer` (RT-07);
   - hashe z `users`, które trywialnie odwrócić (RT-08), zwłaszcza przy słabych lub domyślnych hasłach (RT-09).
3. **Przejęcie sesji agenta przez stored XSS:** RT-04 (komentarz z ładunkiem do dowolnego zgłoszenia, także cudzego) + RT-05 (`innerHTML`). Dalej:
   - RT-07: cookie bez `HttpOnly`, widoczne z portu 5500, bo cookies nie są izolowane po porcie;
   - RT-11: hash w `currentUser`;
   - RT-16: brak CSP, który mógłby zablokować skrypt.
4. **Przejęcie konta bez uwierzytelnienia:** RT-12 (ustalenie loginów) + RT-09 (`admin/admin123`) albo RT-03 (zgadywanie tokenu). Mnożą to RT-07 (brak wygaśnięcia poszerza okno czasowe RT-03) i RT-12 (brak limitów). RT-15 sprawia, że atak przechodzi niezauważony.
5. **Ataki z innego originu:** RT-06 pozwala stronie z tego samego site (inny port na `localhost`) czytać `/api/auth/me` z hashem (RT-11 → RT-08) i wykonywać RT-01 w imieniu ofiary. Jeśli cookie dostanie `SameSite=None`, RT-06 razem z RT-07 daje pełny CSRF z odczytem z dowolnej witryny.
6. **Rekonesans:** RT-14 + RT-10 + RT-13 ujawniają ścieżki, wersje i strukturę bazy, co skraca przygotowanie RT-01.

**Priorytet naprawy:** RT-01, RT-02, RT-03 (krytyczne i niezależne), potem RT-04, RT-05 i RT-07. RT-07 obniża skutki prawie każdej kradzieży sesji.

**Poza zakresem:** A03 (Software Supply Chain) i A08 (Software or Data Integrity) nie dało się ocenić, bo w zakresie nie ma manifestów zależności ani mechanizmów aktualizacji.

**Sprawdzone, bez znalezisk:**
- pozostałe zapytania SQL są parametryzowane;
- `status` w `list_tickets` ogranicza enum `TicketStatus`;
- `update_ticket` wymaga roli agenta i sprawdza przejścia statusów oraz rolę przypisywanego;
- `showMessage` używa `textContent`;
- przy JSON-owym `Content-Type` klasyczny CSRF formularzem nie przechodzi walidacji modeli.

**Odnotowane, niezgłoszone osobno:** brak limitów długości pól tekstowych (CWE-770). Ryzyko jest niskie, a naprawa naturalnie wejdzie przy RT-05 i RT-09.

## 4. Przeczytane pliki

- `backend/app/__init__.py`
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/dependencies.py`
- `backend/app/schemas.py`
- `backend/app/security.py`
- `backend/app/schema.sql`
- `backend/app/routers/__init__.py`
- `backend/app/routers/auth.py`
- `backend/app/routers/health.py`
- `backend/app/routers/tickets.py`
- `frontend/index.html`
- `frontend/app.js`
- `frontend/styles.css`

### Critical Files for Implementation
- `backend/app/routers/tickets.py` — SQLi (RT-01) i IDOR (RT-04)
- `backend/app/routers/auth.py` — rejestracja z rolą (RT-02), cookie i wylogowanie (RT-07), enumeracja (RT-12), błąd 409 (RT-10)
- `backend/app/security.py` — token sesji (RT-03) i haszowanie haseł (RT-08)
- `backend/app/main.py` — CORS (RT-06), handler błędów DB (RT-10), `debug=True` (RT-13)
- `frontend/app.js` — sinki `innerHTML` (RT-05)