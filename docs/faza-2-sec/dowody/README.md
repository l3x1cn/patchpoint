# Dowody Fazy 2

Pliki w tym katalogu dokumentują audyt, naprawę i działanie połatanej aplikacji. Polecenia uruchamiano w katalogu głównym repozytorium, po zadaniach 1–6 planu Fazy 2. Raport z fazy: [`../README.md`](../README.md).

| Plik | Jak powstał | Co dowodzi |
|---|---|---|
| [`ruff-s-faza-1.txt`](ruff-s-faza-1.txt) | `(cd backend && uv run --quiet ruff check --no-cache --select S --output-format concise app) > docs/faza-2-sec/dowody/ruff-s-faza-1.txt` na kodzie Fazy 1 (zadanie 1) | klasyczny SAST (reguły Bandit w Ruff): 3 diagnostyki — S324 ×2 (MD5 w `app/security.py`) i S608 (fałszywie dodatnia w `update_ticket`); SQL injection z W-14 nie został wykryty |
| [`jakosc.txt`](jakosc.txt) | `{ echo '$ make lint'; make lint; echo; echo '$ make typecheck'; make typecheck; } > docs/faza-2-sec/dowody/jakosc.txt 2>&1` | `ruff check` (z regułami `S`) i `ruff format --check` bez uwag; `mypy --strict` bez błędów dla `app` i `tests` (26 plików) |
| [`testy.txt`](testy.txt) | `make test > docs/faza-2-sec/dowody/testy.txt 2>&1` | 122 testy zaliczone, 0 niezaliczonych; pokrycie `TOTAL` 98% (wymagane co najmniej 80%) |
| [`openapi.json`](openapi.json) | `(cd backend && uv run python -c 'import json; from app.main import app; print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))') > docs/faza-2-sec/dowody/openapi.json` | kontrakt API po naprawie wygenerowany przez FastAPI: 10 operacji na 8 ścieżkach; dokumentacja HTTP jest domyślnie wyłączona, więc schemat pobrano z obiektu aplikacji |
| [`poc-faza-1.txt`](poc-faza-1.txt) | `FRONTEND_DIR="$F1/frontend" DB_PATH="$F1/faza1.db" API_LOG="$F1/api.log" ./scripts/security_check.sh > docs/faza-2-sec/dowody/poc-faza-1.txt 2>&1` przy API z drzewa `ab08633` (`git archive`) | PoC na kodzie Fazy 1: 22 × `[PODATNE]`, kod wyjścia 1 |
| [`poc-faza-2.txt`](poc-faza-2.txt) | `DB_PATH="$F2/faza2.db" API_LOG="$F2/api.log" ./scripts/security_check.sh > docs/faza-2-sec/dowody/poc-faza-2.txt 2>&1` przy API z bieżącego kodu | ten sam PoC na kodzie Fazy 2: 22 × `[NAPRAWIONE]`, kod wyjścia 0 |
| [`demo.txt`](demo.txt) | `DEMO_PASSWORD="$DEMO_PASSWORD" make demo > docs/faza-2-sec/dowody/demo.txt 2>&1` przy API ze świeżą bazą i kontami demo | pełny przepływ biznesowy przez HTTP działa po naprawach (logowanie, zgłoszenie, obsługa przez Helpdesk, komentarz, zamknięcie, wyszukiwanie, wylogowanie) |
| [`zdarzenia-bezpieczenstwa.txt`](zdarzenia-bezpieczenstwa.txt) | `grep -F ' patchpoint.security ' "$F2/api.log" > docs/faza-2-sec/dowody/zdarzenia-bezpieczenstwa.txt` | zdarzenia bezpieczeństwa (JSON, logger `patchpoint.security`) zarejestrowane podczas demo i PoC Fazy 2, bez haseł, tokenów i hashy |

Świeże bazy i serwery dla PoC i demo:

```bash
wait_api() { for i in $(seq 1 30); do curl -sf --noproxy '*' http://127.0.0.1:8000/api/health >/dev/null && return 0; sleep 1; done; return 1; }
stop_api() { pkill -f "uvicorn app.main:app --host 127.0.0.1 --port 8000" || true; sleep 1; }

# Faza 1: drzewo ab08633 w katalogu tymczasowym
F1="$(mktemp -d)"
git archive ab08633 backend frontend | tar -x -C "$F1"
(cd "$F1/backend" && uv sync --frozen --quiet)
(cd "$F1/backend" && PATCHPOINT_DATABASE_PATH="$F1/faza1.db" uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 >"$F1/api.log" 2>&1) &

# Faza 2: bieżący kod, konta demo z losowym hasłem
F2="$(mktemp -d)"
DEMO_PASSWORD="Demo-$(python3 -c 'import secrets; print(secrets.token_urlsafe(18))')"
(cd backend && PATCHPOINT_DATABASE_PATH="$F2/faza2.db" PATCHPOINT_SEED_DEMO_DATA=true PATCHPOINT_DEMO_PASSWORD="$DEMO_PASSWORD" uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 >"$F2/api.log" 2>&1) &
```

Po zebraniu dowodów serwer zatrzymywano funkcją `stop_api`, a katalogi tymczasowe usunięto.

## Środowisko

| Parametr | Wartość |
|---|---|
| `date -Iseconds` | `2026-11-16T17:51:29+01:00` |
| `git rev-parse --short HEAD` | `4bfaeb1` (stan kodu, którego dotyczą dowody Fazy 2) |
| `uname -sr` | `Linux 7.2.11-arch1-1` |
| `python3 --version` | `Python 3.14.10` |
| `uv --version` | `uv 0.13.8 (x86_64-unknown-linux-gnu)` |
| `cd backend && uv run python --version` | `Python 3.14.10` |

## Uwagi

- Dowody pochodzą ze świeżych baz w katalogach `mktemp -d`; dane z nich nie trafiły do repozytorium.
- PoC Fazy 1 uruchomiono na drzewie `ab08633` z `git archive`; sam skrypt `scripts/security_check.sh` pochodzi z bieżącego kodu i działa na obu wersjach.
- Pliki zawierają lokalne ścieżki, znaczniki czasu i nazwy kont PoC (`poc.a.<sufiks>`…) i nie były anonimizowane. Znaczniki w `poc-faza-1.txt`, `poc-faza-2.txt` i `demo.txt` są o około minutę wcześniejsze niż czas w tabeli środowiska, który zanotowano po zebraniu dowodów.
- Hasło demo wygenerowano losowo i nigdzie go nie zapisano.
