# Rejestr świadomych uproszczeń (W-01…W-18)

Rejestr powstał w Fazie 1 jako wzorzec („ground truth”) dla Fazy 2 (SEC). Wersja MVP była celowo generowana jako szybki Draft, więc zawiera 18 znanych słabości. Audyt AI w Fazie 2 dostaje wyłącznie kod (`backend/app`, `frontend`) — bez tego pliku i bez `docs/plans` — a jego wyniki porównuje się z poniższą tabelą (trafione, fałszywie dodatnie, pominięte).

Kategorie odpowiadają listie OWASP Top 10:2025 (<https://owasp.org/Top10/2025/>). W kolumnie kategorii pierwsza pozycja jest kategorią główną; kolejne są pomocnicze. Kod nie zawiera komentarzy ani nazw wskazujących te słabości.

| ID | Słabość | Lokalizacja | Wektor scenariusza | OWASP Top 10:2025 | CWE | Objaw (weryfikacja) |
|---|---|---|---|---|---|---|
| W-01 | Gadatliwy handler błędów bazy: 500 z komunikatem SQLite, pełnym SQL, parametrami, ścieżką pliku bazy i tracebackiem | `backend/app/main.py` (handler `DatabaseError`), `backend/app/database.py` | Information Disclosure | A10 Mishandling of Exceptional Conditions | CWE-209, CWE-550 | `GET /api/tickets?search=O'Brien` → 500 z `query`, `database`, `traceback` |
| W-02 | Zajęty login zwraca surowy komunikat ograniczenia SQLite (tabela i kolumna) | `backend/app/routers/auth.py` (`register`) | Information Disclosure | A10 Mishandling of Exceptional Conditions | CWE-209 | 409 `Registration failed: UNIQUE constraint failed: users.username` |
| W-03 | Tryb debug na sztywno (`debug=True`): traceback nieobsłużonych wyjątków; publiczne `/docs`, `/redoc`, `/openapi.json` | `backend/app/main.py` | Information Disclosure | A02 Security Misconfiguration | CWE-489, CWE-215 | `GET /docs` → 200 bez logowania |
| W-04 | `GET /api/health` bez uwierzytelnienia ujawnia bezwzględną ścieżkę bazy i wersje aplikacji, SQLite, Pythona | `backend/app/routers/health.py` | Information Disclosure | A01 Broken Access Control | CWE-497 | pole `database` w odpowiedzi |
| W-05 | Enumeracja kont: 404 dla nieistniejącego loginu, 401 dla złego hasła, różne komunikaty | `backend/app/routers/auth.py` (`login`) | Information Disclosure / Broken Authentication | A07 Authentication Failures | CWE-204 | 404 `User 'x' does not exist` vs 401 `Invalid password` |
| W-06 | Hash hasła w odpowiedziach API (`UserResponse.password_hash`): `/register`, `/login`, `/me` | `backend/app/schemas.py` (`UserResponse`) | Information Disclosure | A01 Broken Access Control | CWE-200 | `GET /api/auth/me` zawiera `password_hash` |
| W-07 | Hasła haszowane MD5 bez soli | `backend/app/security.py` (`hash_password`, `verify_password`) | Broken Authentication | A04 Cryptographic Failures | CWE-328, CWE-916 | hash Jana = `482c811da5d5b4bc6d497ffa98491e38` (MD5 „password123”) |
| W-08 | Przewidywalny token sesji `md5("<login>:<czas_unix>")` | `backend/app/security.py` (`generate_session_token`) | Broken Authentication | A07 Authentication Failures (oraz A04) | CWE-330, CWE-340 | token odtwarzalny z loginu i czasu logowania |
| W-09 | Sesje nigdy nie wygasają (brak TTL i limitu bezczynności) | `backend/app/schema.sql` (`sessions`), `backend/app/dependencies.py` (`get_current_user`) | Broken Authentication | A07 Authentication Failures | CWE-613 | stary token działa bez końca |
| W-10 | Wylogowanie nie unieważnia sesji na serwerze, tylko kasuje cookie | `backend/app/routers/auth.py` (`logout`) | Broken Authentication | A07 Authentication Failures | CWE-613 | po `/logout` token w `Authorization: Bearer` nadal daje 200 na `/me` |
| W-11 | Cookie `session` bez `HttpOnly` i `Secure`; token także w JSON logowania i akceptowany w nagłówku `Authorization` | `backend/app/routers/auth.py` (`login`), `backend/app/dependencies.py` | Broken Authentication | A02 Security Misconfiguration, A07 | CWE-1004, CWE-614 | `Set-Cookie` bez flag; pole `token` w odpowiedzi |
| W-12 | Domyślne konta ze słabymi hasłami tworzone przy starcie na pustej bazie; brak polityki haseł (puste hasło dozwolone); brak limitu prób logowania | `backend/app/database.py` (`DEMO_USERS`, `seed_demo_data`), `backend/app/config.py`, `backend/app/schemas.py` (`UserCreate`) | Broken Authentication | A07 Authentication Failures | CWE-1392, CWE-1393, CWE-521, CWE-307 | logowanie `admin`/`admin123`; rejestracja z `password=""` → 201 |
| W-13 | CORS: `allow_origins=["*"]` + `allow_credentials=True` + wszystkie metody i nagłówki; Starlette odbija dowolny `Origin` z `Allow-Credentials: true` | `backend/app/main.py` | CORS (rozdzielenie frontend/backend) | A02 Security Misconfiguration | CWE-942 | preflight z `Origin: http://evil.example` → ten origin w `Access-Control-Allow-Origin` |
| W-14 | SQL injection w wyszukiwaniu (`search` doklejany f-stringiem do `LIKE`); z W-01 ujawnia strukturę bazy | `backend/app/routers/tickets.py` (`list_tickets`) | Information Disclosure (łańcuch z W-01) | A05 Injection | CWE-89 | `search=') OR 1=1 OR ('` → pracownik widzi cudze zgłoszenia |
| W-15 | Mass assignment: pole `role` w rejestracji pozwala nadać sobie rolę `agent` | `backend/app/schemas.py` (`UserCreate`), `backend/app/routers/auth.py` (`register`) | Broken Authentication (eskalacja uprawnień) | A08 Software or Data Integrity Failures, A01 | CWE-915 | rejestracja z `"role": "agent"` → konto agenta |
| W-16 | IDOR: szczegóły zgłoszenia i komentarze bez sprawdzenia, czy pracownik jest zgłaszającym | `backend/app/routers/tickets.py` (`get_ticket`, `add_comment`) | Information Disclosure | A01 Broken Access Control | CWE-639 | `anna.nowak` czyta `GET /api/tickets/1` (zgłoszenie Jana) |
| W-17 | Stored XSS: dane z API wstawiane przez `innerHTML` bez escapowania; skrypt odczyta cookie `session` (brak `HttpOnly`, W-11) | `frontend/app.js` | Broken Authentication (kradzież sesji) | A05 Injection | CWE-79 | tytuł `<img src=x onerror=...>` wykonuje skrypt |
| W-18 | Brak logowania i alertowania zdarzeń bezpieczeństwa (nieudane logowania, rejestracje, zmiany ról) | `backend/app` | utrudnione wykrycie ataków | A09 Security Logging & Alerting Failures | CWE-778 | brak użycia modułu `logging` w `backend/app` |

## Podsumowanie

Wszystkie 18 pozycji zweryfikowano w kodzie na commicie `8a968e9`; żadna z nich nie jest nieobecna, a lokalizacje z tabeli zgadzają się z kodem.

Według wektora scenariusza:

| Wektor | Liczba | Pozycje |
|---|---|---|
| Information Disclosure | 7 | W-01, W-02, W-03, W-04, W-06, W-14, W-16 |
| Information Disclosure / Broken Authentication | 1 | W-05 |
| Broken Authentication | 8 | W-07, W-08, W-09, W-10, W-11, W-12, W-15, W-17 |
| CORS (rozdzielenie frontend/backend) | 1 | W-13 |
| utrudnione wykrycie ataków (brak wektora wprost) | 1 | W-18 |
| **Razem** | **18** | |

Według kategorii głównej OWASP Top 10:2025 (kategorie pomocnicze: W-08 także A04, W-11 także A07, W-15 także A01):

| Kategoria | Liczba | Pozycje |
|---|---|---|
| A01 Broken Access Control | 3 | W-04, W-06, W-16 |
| A02 Security Misconfiguration | 3 | W-03, W-11, W-13 |
| A04 Cryptographic Failures | 1 | W-07 |
| A05 Injection | 2 | W-14, W-17 |
| A07 Authentication Failures | 5 | W-05, W-08, W-09, W-10, W-12 |
| A08 Software or Data Integrity Failures | 1 | W-15 |
| A09 Security Logging & Alerting Failures | 1 | W-18 |
| A10 Mishandling of Exceptional Conditions | 2 | W-01, W-02 |
| **Razem** | **18** | |
