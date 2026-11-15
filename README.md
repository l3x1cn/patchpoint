# PatchPoint — system zgłoszeń IT (Helpdesk)

PatchPoint to system do zgłaszania awarii sprzętu IT przez pracowników do działu Helpdesk, zbudowany jako projekt kursu „AI-Driven DevSecOps”, Scenariusz 5 (Menadżer Zadań IT). Backend (Python, FastAPI, SQLite) i minimalny frontend (HTML/JS) działają na osobnych originach.

> **Uwaga:** wersja z Fazy 1 to celowo podatne MVP (patrz [rejestr słabości](docs/faza-1-dev/rejestr-slabosci.md)). Uruchamiaj ją wyłącznie lokalnie; nie wdrażaj jej i nie wystawiaj do sieci.

## Status faz

| Faza | Rola | Zakres | Status | Dokumentacja |
|---|---|---|---|---|
| Faza 1 | DEV | generowanie kodu z AI: backend, frontend, baza SQLite, celowe uproszczenia (Draft/MVP) | zrealizowana | [docs/faza-1-dev/README.md](docs/faza-1-dev/README.md) |
| Faza 2 | SEC | audyt SAST z AI, threat modeling, poprawki | do realizacji | — |
| Faza 3 | OPS | Dockerfile, CI/CD z Semgrep i Trivy, architektura sieci | do realizacji | — |

## Architektura w skrócie

Statyczny frontend (`http://localhost:5500`) wywołuje przez `fetch` z cookie sesyjnym API FastAPI (`http://localhost:8000`), które zapisuje dane w pliku SQLite. Szczegóły, diagramy i opis API znajdują się w [raporcie z Fazy 1](docs/faza-1-dev/README.md).

## Struktura repozytorium

```text
.
├── Makefile                  # cele: install, run, test, lint, format, typecheck, frontend, demo
├── README.md                 # ten plik
├── backend/                  # API FastAPI (projekt uv)
│   ├── .python-version       # przypięta wersja Pythona (3.14)
│   ├── pyproject.toml        # zależności i konfiguracja pytest, ruff, mypy
│   ├── uv.lock               # zablokowane wersje zależności
│   ├── app/
│   │   ├── main.py           # fabryka aplikacji, CORS, obsługa błędów bazy
│   │   ├── config.py         # ustawienia ze zmiennych PATCHPOINT_*
│   │   ├── database.py       # połączenie SQLite, helpery zapytań, dane demo
│   │   ├── schema.sql        # definicja tabel users, sessions, tickets, comments
│   │   ├── schemas.py        # modele Pydantic i enumy
│   │   ├── security.py       # haszowanie haseł i generowanie tokenów sesji
│   │   ├── dependencies.py   # zależności FastAPI: baza, bieżący użytkownik, rola agenta
│   │   └── routers/          # endpointy: health, auth, tickets
│   └── tests/                # testy pytest logiki biznesowej i kontraktów API
├── frontend/                 # statyczny klient: index.html, app.js, styles.css
├── scripts/
│   └── demo.sh               # scenariusz end-to-end przez curl i jq
└── docs/
    ├── faza-1-dev/           # raport Fazy 1, dziennik promptów, rejestr słabości, dowody
    └── plans/                # plan implementacji Fazy 1
```

## Wymagania

- Python ≥ 3.12 (projekt przypięty do 3.14 przez `backend/.python-version`),
- [uv](https://docs.astral.sh/uv/),
- make,
- curl i jq (do `make demo`),
- przeglądarka.

## Szybki start

```bash
make install     # instalacja zależności (uv sync)
make run         # API: http://localhost:8000, Swagger: http://localhost:8000/docs
make frontend    # w drugim terminalu; UI: http://localhost:5500
make test        # testy z pokryciem (próg 80%)
make demo        # scenariusz end-to-end; wymaga działającego API (make run)
```

Interfejs otwieraj przez `http://localhost:5500` (nie `127.0.0.1`), aby cookie sesyjne z `localhost:8000` było przesyłane z żądaniami.

Reset danych: usuń plik `backend/data/patchpoint.db`; konta i zgłoszenia demo zostaną odtworzone przy następnym starcie API.

Konfiguracja przez zmienne środowiskowe:

| Zmienna | Znaczenie | Wartość domyślna |
|---|---|---|
| `PATCHPOINT_DATABASE_PATH` | ścieżka pliku bazy SQLite | `backend/data/patchpoint.db` |
| `PATCHPOINT_SEED_DEMO_DATA` | tworzenie kont i zgłoszeń demo na pustej bazie | `true` |

## Konta demo

| Login | Hasło | Rola |
|---|---|---|
| `admin` | `admin123` | agent Helpdesk |
| `helpdesk` | `helpdesk123` | agent Helpdesk |
| `jan.kowalski` | `password123` | pracownik |
| `anna.nowak` | `password123` | pracownik |

## Polecenia make

| Cel | Działanie |
|---|---|
| `make install` | instaluje zależności backendu (`uv sync`) |
| `make run` | uruchamia API na `127.0.0.1:8000` (`API_HOST`, `API_PORT`) |
| `make test` | uruchamia testy pytest z raportem pokrycia |
| `make lint` | `ruff check` i `ruff format --check` |
| `make format` | `ruff format` i `ruff check --fix` |
| `make typecheck` | `mypy` (tryb strict) dla `app` i `tests` |
| `make frontend` | serwuje `frontend/` na `127.0.0.1:5500` (`FRONTEND_PORT`) |
| `make demo` | uruchamia `scripts/demo.sh` względem `API_URL` (domyślnie `http://127.0.0.1:8000`) |

## Dokumentacja

- [Raport z Fazy 1 (DEV)](docs/faza-1-dev/README.md)
- [Dziennik promptów AI](docs/faza-1-dev/prompty.md)
- [Rejestr słabości W-01…W-18](docs/faza-1-dev/rejestr-slabosci.md)
- [Dowody uruchomienia](docs/faza-1-dev/dowody/README.md)
- [Plan implementacji Fazy 1](docs/plans/2026-11-15-faza-1-mvp.md)
