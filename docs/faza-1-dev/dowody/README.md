# Dowody uruchomienia Fazy 1

Pliki w tym katalogu dokumentują, że kod z Fazy 1 przechodzi bramki jakości, testy i scenariusz end-to-end. Wszystkie polecenia uruchamiano w katalogu głównym repozytorium.

| Plik | Jak powstał | Co dowodzi |
|---|---|---|
| [`jakosc.txt`](jakosc.txt) | `{ echo '$ make lint'; make lint; echo; echo '$ make typecheck'; make typecheck; } > docs/faza-1-dev/dowody/jakosc.txt 2>&1` | `ruff check` i `ruff format --check` bez uwag oraz `mypy --strict` bez błędów dla `app` i `tests` |
| [`testy.txt`](testy.txt) | `make test > docs/faza-1-dev/dowody/testy.txt 2>&1` | 46 testów zaliczonych, 0 niezaliczonych; pokrycie `TOTAL` 96% (wymagane co najmniej 80%) |
| [`demo.txt`](demo.txt) | `make demo > docs/faza-1-dev/dowody/demo.txt 2>&1` przy API uruchomionym na świeżej bazie (patrz niżej) | pełny przepływ biznesowy przez HTTP: logowanie, zgłoszenie, obsługa przez Helpdesk, komentarz, zamknięcie, wyszukiwanie, wylogowanie |
| [`openapi.json`](openapi.json) | `curl -s http://127.0.0.1:8000/openapi.json \| jq . > docs/faza-1-dev/dowody/openapi.json` | kontrakt API wygenerowany przez FastAPI: 10 operacji na 8 ścieżkach |

Świeża baza i serwer dla `demo.txt` i `openapi.json`:

```bash
DEMO_DIR="$(mktemp -d)"
(cd backend && exec env PATCHPOINT_DATABASE_PATH="$DEMO_DIR/demo.db" uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 >"$DEMO_DIR/api.log" 2>&1) &
```

Po zebraniu dowodów serwer zatrzymano (`kill` oraz `pkill -f "uvicorn app.main:app --host 127.0.0.1 --port 8000"`).

## Środowisko

| Parametr | Wartość |
|---|---|
| `date -Iseconds` | `2026-11-15T20:55:07+01:00` |
| `git rev-parse --short HEAD` | `8a968e9` (stan kodu, którego dotyczą dowody) |
| `uname -sr` | `Linux 7.2.11-arch1-1` |
| `python3 --version` | `Python 3.14.9` |
| `uv --version` | `uv 0.13.8 (x86_64-unknown-linux-gnu)` |
| `cd backend && uv run python --version` | `Python 3.14.9` |

## Uwagi

- Dowody pochodzą ze świeżej bazy demo utworzonej poza repozytorium (katalog tymczasowy z `mktemp -d`); dane z niej nie trafiły do repozytorium.
- Pliki zawierają lokalne ścieżki oraz znaczniki czasu (np. pole `Data:` w `demo.txt`, które jest kilkanaście sekund wcześniejsze niż czas w tabeli środowiska) i nie były anonimizowane.
- Zgodnie z założeniem Fazy 1 testy nie utrwalają celowych słabości z [`rejestru słabości`](../rejestr-slabosci.md); dowodem ich istnienia jest kod i opisane tam objawy.
