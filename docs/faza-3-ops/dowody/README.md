# Dowody Fazy 3

Pliki w tym katalogu dokumentują skanowanie, budowę i działanie obrazów oraz stosu, walidację playbooka Ansible i przebieg potoku CI. Polecenia uruchamiano w katalogu głównym repozytorium, po zadaniach 1–8 planu Fazy 3 (`E=docs/faza-3-ops/dowody`). Raport z fazy: [`../README.md`](../README.md).

| Plik | Jak powstał | Co dowodzi |
|---|---|---|
| [`jakosc.txt`](jakosc.txt) | `{ echo '$ make lint'; make lint; echo; echo '$ make typecheck'; make typecheck; } > "$E/jakosc.txt" 2>&1` | `ruff check` (z regułami `S`) i `ruff format --check` bez uwag (29 plików), `mypy --strict` bez błędów (29 plików) |
| [`testy.txt`](testy.txt) | `make test > "$E/testy.txt" 2>&1` | 145 testów zaliczonych, 0 niezaliczonych; pokrycie `TOTAL` 98% (98,32%; wymagane co najmniej 80%); w tym testy nazwy ciasteczka sesji |
| [`obrazy.txt`](obrazy.txt) | `docker image inspect` (użytkownik, porty, healthcheck, etykiety OCI), `docker image ls`, `grep -n '^FROM' backend/Dockerfile deploy/proxy/Dockerfile` i sprawdzenie braku pip w obrazie API; każdy blok poprzedzony linią `$ <polecenie>` | obraz API działa jako `10001:10001`, proxy jako `nginx`; oba mają HEALTHCHECK i etykiety `source`, `revision`, `title`; wszystkie `FROM` są przypięte digestem; w obrazie API nie ma pip; rozmiary 214 MB (API) i 147 MB (proxy) |
| [`semgrep.txt`](semgrep.txt) | `make semgrep > "$E/semgrep.txt" 2>&1` | Semgrep 1.185.0: 275 reguł na 69 plikach, 0 znalezisk; linia `Bramka Semgrep: brak znalezisk` |
| [`trivy-fs.txt`](trivy-fs.txt) | `make trivy-fs > "$E/trivy-fs.txt" 2>&1` | Trivy 0.76.2 na drzewie repozytorium: 0 podatności w `backend/uv.lock`, 0 błędów konfiguracji w obu Dockerfile, brak sekretów |
| [`trivy-obrazy.txt`](trivy-obrazy.txt) | `make images > /dev/null 2>&1 && make trivy-images > "$E/trivy-obrazy.txt" 2>&1` | brak HIGH i CRITICAL z poprawką w obrazie API (Debian 13.7) i proxy (Alpine 3.24.4), przy 6 wyjątkach `.trivyignore` dla nginx |
| [`smoke-stosu.txt`](smoke-stosu.txt) | `make stack-smoke > "$E/smoke-stosu.txt" 2>&1` | 27 kontroli `[OK]`, 0 `[BŁĄD]`: PoC z Fazy 2 w kontenerze API (22 × `[NAPRAWIONE]`), demo przez proxy, TLS i HSTS, WAF, ciasteczko `__Host-session`, `client_ip`, izolacja sieci, limit żądań; ostatnia linia `STACK SMOKE ZAKOŃCZONY POWODZENIEM` |
| [`ansible-lint.txt`](ansible-lint.txt) | `make ansible-lint > "$E/ansible-lint.txt" 2>&1` | `ansible-lint` w profilu `production` bez naruszeń i `ansible-playbook --syntax-check` bez błędów; playbook nie był uruchamiany na serwerze |
| [`triaz-skanow.md`](triaz-skanow.md) | zapisywany w zadaniach 3–9 | każde znalezisko skanerów z decyzją (naprawione, wyjątek) i podsumowania po kolejnych zadaniach |
| [`ci.md`](ci.md) | zadanie 8: `gh run list`, `gh run view`, `gh api` dla przebiegów na GitHub Actions | przebieg potoku CI: pierwszy przebieg z błędem środowiska runnera, poprawka i przebieg zakończony wynikiem `success` |

## Środowisko

| Parametr | Wartość |
|---|---|
| `date -Iseconds` | `2026-11-19T08:24:40+01:00` |
| `git rev-parse --short HEAD` | `fe314cb + zmiany zadania 9` (stan kodu, którego dotyczą dowody; zadanie 9 dodaje tylko dokumentację) |
| `uname -sr` | `Linux 7.3.4-arch1-2` |
| `docker version --format '{{.Server.Version}}'` | `29.9.3` |
| `docker compose version --short` | `5.8.0` |
| `uv --version` | `uv 0.13.8 (x86_64-unknown-linux-gnu)` |
| `python3 --version` | `Python 3.14.10` |

## Uwagi

- Pliki zawierają lokalne ścieżki i znaczniki czasu i nie były anonimizowane.
- Hasła demo w smoke są losowe i nigdzie niezapisane; pliki nie zawierają haseł ani tokenów sesji.
- Obrazy w `obrazy.txt` i `trivy-obrazy.txt` zbudowano lokalnie (`make images`); CI buduje własne obrazy z tego samego kodu ([`ci.md`](ci.md)).
- Pełne wyniki skanerów (JSON i SARIF) leżą w ignorowanym przez git katalogu `reports/`; w CI trafiają do artefaktów przebiegu.
- Wyniki zależą od dnia skanu: baza podatności Trivy i pakiety Debiana w obrazie API zmieniają się w czasie.
