# Przebieg potoku CI — Faza 3

Plik dokumentuje uruchomienia potoku `.github/workflows/ci.yml` na GitHub Actions dla gałęzi `delivery/faza-3-ops`: pierwszy przebieg zakończony błędem (różnica środowiska runnera), poprawkę oraz zielony przebieg ze sprawdzenia poprawki na tymczasowej gałęzi `ci-check/faza-3-ops`. Dowodzi, że joby `quality`, `semgrep`, `trivy-fs`, `ansible` i `build` (budowa obrazów, bramka Trivy obrazów, smoke stosu) przechodzą na runnerze `ubuntu-24.04`, a `publish` jest pomijany poza pushem na `main`. Raport Sekcji Ops: [../README.md](../README.md).

## Przebieg

Zielony przebieg (sprawdzenie poprawki, drzewo różni się od commita dowodów tylko plikiem `ci.md`):

| Parametr | Wartość |
|---|---|
| PR | [#4](https://github.com/l3x1cn/patchpoint/pull/4) (tymczasowy, draft, `ci-check/faza-3-ops` → `main`; zamknięty, gałąź usunięta) |
| Gałąź | `ci-check/faza-3-ops` |
| Commit (`headSha`) | `2d9948e86b2c2b42d3de35c926cab76ebb94f778` |
| Przebieg | https://github.com/l3x1cn/patchpoint/actions/runs/44477934521 |
| Zdarzenie | `pull_request` |
| Data | 2026-11-19 |
| Wynik | `success` |

Docelowy draft PR: [#3](https://github.com/l3x1cn/patchpoint/pull/3) (`delivery/faza-3-ops` → `main`). Jego pierwszy przebieg (patrz „Przebiegi nieudane i poprawki”) dotyczył commita `4f16a2b5772ece83e85548b8d9cae753f743a7cf`, bez poprawki.

## Joby

Zielony przebieg 44477934521:

| Job | Wynik | Czas |
|---|---|---|
| `quality` | `success` | 0 min 57 s |
| `semgrep` | `success` | 0 min 34 s |
| `trivy-fs` | `success` | 0 min 25 s |
| `ansible` | `success` | 0 min 32 s |
| `build` | `success` | 1 min 21 s |
| `publish` | `skipped` | 0 min 0 s |

`publish` działa tylko przy pushu na `main`, więc w pull requeście jest pomijany; publikacja w GHCR nie została sprawdzona (nastąpi po scaleniu).

## Artefakty

Zielony przebieg 44477934521:

| Artefakt | Rozmiar (bajty) |
|---|---|
| `semgrep` | 116497 |
| `trivy-fs` | 2222 |
| `build-reports` | 83796 |
| `images` | 88479228 |

## Przebiegi nieudane i poprawki

Pierwszy przebieg na `delivery/faza-3-ops` (https://github.com/l3x1cn/patchpoint/actions/runs/44477002456, commit `4f16a2b5772ece83e85548b8d9cae753f743a7cf`, zdarzenie `pull_request`, 2026-11-19) zakończył się wynikiem `failure`:

| Job | Wynik | Czas |
|---|---|---|
| `quality` | `success` | 0 min 57 s |
| `semgrep` | `success` | 0 min 34 s |
| `trivy-fs` | `success` | 0 min 22 s |
| `ansible` | `success` | 0 min 32 s |
| `build` | `failure` | 1 min 47 s |
| `publish` | `skipped` | 0 min 0 s |

- Przyczyna: w jobie `build` krok „Smoke obrazów i stosu compose” zatrzymał się w części 2 (kontener API nie odpowiedział na `/api/health` w ciągu 60 s). Log kontenera: `ImportError: cannot import name 'auth' from 'app.routers' (unknown location)`. Budowa obrazów i bramka Trivy przeszły. Przyczyną było symboliczne `COPY --chmod=u=rwX,go=rX` przy kopiowaniu katalogu z podkatalogami: BuildKit w Dockerze 28.0.4 na runnerze nadaje podkatalogom tryb `drw-r--r--` (bez bitu `x`), więc proces bez uprawnień roota nie mógł wejść do `app/routers`. Lokalny Docker 29.9.3 stosuje `X` poprawnie, dlatego błąd ujawnił się dopiero w CI. Odtworzono go lokalnie na builderze `moby/buildkit:v0.20.1`.
- Poprawka: `backend/Dockerfile` kopiuje `app` bez `--chmod` i ustawia tryb poleceniem `chmod -R u=rwX,go=rX /app/app` w istniejącym kroku `RUN` (przed `USER 10001:10001`); `deploy/proxy/Dockerfile` ten sam problem miał dla katalogu `deploy/proxy/templates/` (podkatalogi `conf.d` i `includes`), więc tam tryb ustawia `RUN chmod -R u=rwX,go=rX /etc/nginx/templates` (z `USER root` na czas tego kroku; końcowy `USER nginx` bez zmian). Kopiowanie samych plików (`COPY --chmod` bez podkatalogów) zostało bez zmian. Pliki te nie należały do listy zadania, ale tylko w nich można było usunąć przyczynę.
- Potwierdzenie lokalne: `make images && make stack-smoke` → `STACK SMOKE ZAKOŃCZONY POWODZENIEM`; obrazy zbudowane na builderze `moby/buildkit:v0.20.1` mają podkatalogi w trybie `drwxr-xr-x`.
- Sprawdzenie na GitHubie: tymczasowa gałąź `ci-check/faza-3-ops` z poprawką, draft PR #4, przebieg 44477934521 (tabele wyżej) zakończony wynikiem `success`; po sprawdzeniu PR #4 zamknięto, a gałąź usunięto. Wystarczyła jedna próba z trzech dopuszczalnych.
