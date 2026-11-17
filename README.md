# PatchPoint — system zgłoszeń IT (Helpdesk)

PatchPoint to system do zgłaszania awarii sprzętu IT przez pracowników do działu Helpdesk, zbudowany jako projekt kursu „AI-Driven DevSecOps”, Scenariusz 5 (Menadżer Zadań IT). Backend (Python, FastAPI, SQLite) i minimalny frontend (HTML/JS) działają na osobnych originach.

> **Uwaga:** wersja z Fazy 1 (commit `ab08633`) była celowo podatnym MVP (patrz [rejestr słabości](docs/faza-1-dev/rejestr-slabosci.md)). Bieżąca wersja zawiera poprawki z Fazy 2 (patrz [raport z Fazy 2](docs/faza-2-sec/README.md)). Do czasu Fazy 3 (TLS, kontener, CI) uruchamiaj ją wyłącznie lokalnie.

## Status faz

| Faza | Rola | Zakres | Status | Dokumentacja |
|---|---|---|---|---|
| Faza 1 | DEV | generowanie kodu z AI: backend, frontend, baza SQLite, celowe uproszczenia (Draft/MVP) | zrealizowana | [docs/faza-1-dev/README.md](docs/faza-1-dev/README.md) |
| Faza 2 | SEC | audyt SAST z AI, threat modeling, poprawki | zrealizowana | [docs/faza-2-sec/README.md](docs/faza-2-sec/README.md) |
| Faza 3 | OPS | Dockerfile, CI/CD z Semgrep i Trivy, architektura sieci | do realizacji | — |

## Architektura w skrócie

Statyczny frontend (`http://localhost:5500`) wywołuje przez `fetch` z cookie sesyjnym (`HttpOnly; Secure; SameSite=Strict`) API FastAPI (`http://localhost:8000`), które zapisuje dane w pliku SQLite. API przyjmuje żądania tylko z originów z listy `PATCHPOINT_CORS_ORIGINS` (domyślnie `http://localhost:5500`). Szczegóły, diagramy i opis API znajdują się w [raporcie z Fazy 1](docs/faza-1-dev/README.md), a opis zabezpieczeń w [raporcie z Fazy 2](docs/faza-2-sec/README.md).

## Struktura repozytorium

```text
.
├── .av/                      # konfiguracja QA
│   ├── config.toml           # środowisko i użytkownicy QA (w repozytorium)
│   ├── secrets.local.env     # dane logowania agenta QA (lokalny, ignorowany przez git)
│   └── run/                  # baza, logi i pgid uruchomień QA (lokalny, ignorowany przez git)
├── Makefile                  # cele: install, run, test, lint, format, typecheck, frontend, demo, security-check
├── README.md                 # ten plik
├── backend/                  # API FastAPI (projekt uv)
│   ├── .python-version       # przypięta wersja Pythona (3.14)
│   ├── pyproject.toml        # zależności i konfiguracja pytest, ruff (z regułami S), mypy
│   ├── uv.lock               # zablokowane wersje zależności
│   ├── app/
│   │   ├── main.py           # fabryka aplikacji, CORS, nagłówki, limit ciała, ogólna obsługa błędów
│   │   ├── config.py         # ustawienia ze zmiennych PATCHPOINT_*
│   │   ├── audit.py          # logowanie zdarzeń bezpieczeństwa (JSON) i konfiguracja loggerów
│   │   ├── middleware.py     # SecurityHeadersMiddleware (nagłówki bezpieczeństwa)
│   │   ├── database.py       # połączenie SQLite, transaction()/run(), wersja schematu, dane demo
│   │   ├── schema.sql        # tabele users, sessions, login_failures, tickets, comments; user_version
│   │   ├── schemas.py        # modele Pydantic (walidacja i limity) i enumy
│   │   ├── security.py       # Argon2id, polityka haseł, tokeny sesji i ich SHA-256
│   │   ├── sessions.py       # cykl życia sesji i limit prób logowania
│   │   ├── dependencies.py   # zależności FastAPI: baza, bieżący użytkownik, rola agenta
│   │   └── routers/          # endpointy: health, auth, tickets
│   └── tests/                # testy pytest logiki biznesowej, kontraktów API i zabezpieczeń
├── frontend/                 # statyczny klient: index.html (z CSP), app.js, styles.css
├── scripts/
│   ├── demo.sh               # scenariusz end-to-end przez curl i jq
│   └── security_check.sh     # PoC regresji bezpieczeństwa: 22 sprawdzenia, [PODATNE]/[NAPRAWIONE]
└── docs/
    ├── faza-1-dev/           # raport Fazy 1, dziennik promptów, rejestr słabości, dowody
    ├── faza-2-sec/           # raport Fazy 2, audyt Red Team, threat model, dziennik promptów, dowody
    ├── plans/                # plany implementacji Faz 1 i 2
    ├── reviews/              # raporty code review
    └── testing/              # plany i raporty QA
```

## Wymagania

- Python ≥ 3.12 (projekt przypięty do 3.14 przez `backend/.python-version`),
- [uv](https://docs.astral.sh/uv/),
- make,
- curl i jq (do `make demo` i `make security-check`),
- python3 (do `make security-check`),
- przeglądarka. Chrome i Firefox przyjmują ciasteczko `Secure` na `http://localhost`; Safari nie — w nim uruchom API z `PATCHPOINT_COOKIE_SECURE=false`.

## Szybki start

```bash
make install     # instalacja zależności (uv sync)
make run         # API: http://localhost:8000, startuje z pustą bazą bez kont
make frontend    # w drugim terminalu; UI: http://localhost:5500
make test        # testy z pokryciem (próg 80%)
```

Dane demo (konta i zgłoszenia) powstają tylko na żądanie, z hasłem podanym przez zmienną środowiskową:

```bash
export PATCHPOINT_DEMO_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(18))')"
PATCHPOINT_SEED_DEMO_DATA=true make run
```

W drugim terminalu, z tym samym hasłem:

```bash
DEMO_PASSWORD="$PATCHPOINT_DEMO_PASSWORD" make demo   # scenariusz end-to-end; wymaga działającego API z danymi demo
make security-check                                    # PoC bezpieczeństwa; wymaga działającego API
```

Swagger (`http://localhost:8000/docs`) jest dostępny tylko po uruchomieniu API z `PATCHPOINT_DOCS_ENABLED=true`.

Interfejs otwieraj przez `http://localhost:5500` (nie `127.0.0.1`), aby cookie sesyjne z `localhost:8000` było przesyłane z żądaniami, a origin zgadzał się z listą CORS.

Reset danych: usuń plik `backend/data/patchpoint.db`.

### Migracja z Fazy 1

API odmawia startu na bazie utworzonej w Fazie 1, bo schemat (sesje z hashowanymi tokenami, tabela `login_failures`, hasła Argon2id) jest niezgodny. Usuń `backend/data/patchpoint.db` i uruchom API ponownie; baza zostanie utworzona od nowa.

### Konfiguracja

Zmienne środowiskowe:

| Zmienna | Znaczenie | Wartość domyślna |
|---|---|---|
| `PATCHPOINT_DATABASE_PATH` | ścieżka pliku bazy SQLite | `backend/data/patchpoint.db` |
| `PATCHPOINT_SEED_DEMO_DATA` | tworzenie kont i zgłoszeń demo na pustej bazie | `false` |
| `PATCHPOINT_DEMO_PASSWORD` | hasło kont demo; wymagane przy `PATCHPOINT_SEED_DEMO_DATA=true`, co najmniej 15 znaków, bez loginów kont demo | brak |
| `PATCHPOINT_DOCS_ENABLED` | udostępnia `/docs`, `/redoc` i `/openapi.json` | `false` |
| `PATCHPOINT_CORS_ORIGINS` | dozwolone originy CORS (lista JSON); `*` jest odrzucane | `["http://localhost:5500"]` |
| `PATCHPOINT_COOKIE_SECURE` | atrybut `Secure` ciasteczka sesyjnego | `true` |
| `PATCHPOINT_SESSION_IDLE_MINUTES` | wygaśnięcie sesji po bezczynności | `30` |
| `PATCHPOINT_SESSION_ABSOLUTE_MINUTES` | maksymalny czas życia sesji | `480` |
| `PATCHPOINT_LOGIN_MAX_FAILURES` | liczba nieudanych prób logowania na konto w oknie blokady | `5` |
| `PATCHPOINT_LOGIN_LOCKOUT_MINUTES` | długość okna blokady logowania | `15` |
| `PATCHPOINT_MAX_BODY_BYTES` | maksymalny rozmiar ciała żądania (413 powyżej) | `65536` |

## Konta demo

Konta powstają tylko przy `PATCHPOINT_SEED_DEMO_DATA=true`; hasło wszystkich kont to wartość `PATCHPOINT_DEMO_PASSWORD`. Konta `admin` nie ma.

| Login | Rola |
|---|---|
| `helpdesk` | agent Helpdesk |
| `jan.kowalski` | pracownik |
| `anna.nowak` | pracownik |

## Polecenia make

| Cel | Działanie |
|---|---|
| `make install` | instaluje zależności backendu (`uv sync`) |
| `make run` | uruchamia API na `127.0.0.1:8000` (`API_HOST`, `API_PORT`) |
| `make test` | uruchamia testy pytest z raportem pokrycia |
| `make lint` | `ruff check` (z regułami bezpieczeństwa `S`) i `ruff format --check` |
| `make format` | `ruff format` i `ruff check --fix` |
| `make typecheck` | `mypy` (tryb strict) dla `app` i `tests` |
| `make frontend` | serwuje `frontend/` na `127.0.0.1:5500` (`FRONTEND_PORT`) |
| `make demo` | uruchamia `scripts/demo.sh` względem `API_URL` (domyślnie `http://127.0.0.1:8000`); wymaga `DEMO_PASSWORD` |
| `make security-check` | uruchamia `scripts/security_check.sh` względem `API_URL`: 22 sprawdzenia regresji bezpieczeństwa |

## Dokumentacja

- [Raport z Fazy 1 (DEV)](docs/faza-1-dev/README.md)
- [Dziennik promptów AI — Faza 1](docs/faza-1-dev/prompty.md)
- [Rejestr słabości W-01…W-18](docs/faza-1-dev/rejestr-slabosci.md)
- [Dowody uruchomienia — Faza 1](docs/faza-1-dev/dowody/README.md)
- [Raport z Fazy 2 (SEC) — Sekcja Sec raportu DevSecOps](docs/faza-2-sec/README.md)
- [Threat model](docs/faza-2-sec/threat-model.md)
- [Audyt Red Team z AI](docs/faza-2-sec/audyt-red-team.md)
- [Dziennik promptów AI — Faza 2](docs/faza-2-sec/prompty.md)
- [Dowody — Faza 2](docs/faza-2-sec/dowody/README.md)
- [Raport QA Fazy 1](docs/testing/reports/2026-11-16-patchpoint-helpdesk-mvp-report.md)
- [Raport code review Fazy 1](docs/reviews/2026-11-16-delivery-faza-1-mvp.md)
- [Plan implementacji Fazy 1](docs/plans/2026-11-15-faza-1-mvp.md)
- [Plan implementacji Fazy 2](docs/plans/2026-11-16-faza-2-sec.md)
