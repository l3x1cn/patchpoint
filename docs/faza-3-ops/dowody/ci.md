# Przebieg potoku CI — Faza 3

Plik dokumentuje uruchomienia potoku `.github/workflows/ci.yml` na GitHub Actions dla gałęzi `delivery/faza-3-ops` (draft PR #3). Głównym dowodem jest zielony przebieg 44520467614 na rzeczywistej gałęzi delivery: joby `quality`, `semgrep`, `trivy-fs`, `ansible` i `build` (budowa obrazów, bramka Trivy obrazów, smoke stosu) przechodzą na runnerze `ubuntu-24.04`, a `publish` jest pomijany poza pushem na `main`. Wcześniejsze przebiegi — dwa zakończone błędem i jedno sprawdzenie poprawki na tymczasowej gałęzi — opisuje część „Przebiegi nieudane i poprawki”. Raport Sekcji Ops: [../README.md](../README.md).

## Przebieg

Zielony przebieg na końcowym stanie gałęzi delivery:

| Parametr | Wartość |
|---|---|
| PR | [#3](https://github.com/l3x1cn/patchpoint/pull/3) (draft, `delivery/faza-3-ops` → `main`) |
| Gałąź | `delivery/faza-3-ops` |
| Commit (`headSha`) | `26d93eb41cb3bc851ead7ce5f5f8e530131717a2` |
| Przebieg | https://github.com/l3x1cn/patchpoint/actions/runs/44520467614 |
| Zdarzenie | `pull_request` |
| Data | 2026-11-19 (utworzony 12:04:21 UTC) |
| Wynik | `success` |

Przebieg `44520467614` na commicie `26d93eb` to ostatni zapisany przebieg potoku dla dostarczonego stanu. Kolejne commity tej gałęzi (poprawki z przeglądu) zmieniają kod i dokumentację, a ich przebiegi CI nie są opisane w tym pliku.

## Joby

Zielony przebieg 44520467614 (godziny w UTC, 2026-11-19):

| Job | Wynik | Czas |
|---|---|---|
| `quality` | `success` | 0 min 56 s (12:04:25–12:05:21) |
| `semgrep` | `success` | 0 min 34 s (12:04:24–12:04:58) |
| `trivy-fs` | `success` | 0 min 35 s (12:04:24–12:04:59) |
| `ansible` | `success` | 1 min 10 s (12:04:25–12:05:35) |
| `build` | `success` | 1 min 26 s (12:05:38–12:07:04) |
| `publish` | `skipped` | 0 min 0 s |

`publish` działa tylko przy pushu na `main`, więc w pull requeście jest pomijany; publikacja w GHCR nie została sprawdzona (nastąpi po scaleniu).

## Artefakty

Zielony przebieg 44520467614:

| Artefakt | Rozmiar (bajty) |
|---|---|
| `trivy-fs` | 2225 |
| `semgrep` | 116490 |
| `images` | 88701333 |
| `build-reports` | 92870 |

## Przebiegi nieudane i poprawki

Chronologicznie: dwa przebiegi zakończone błędem (każdy z inną przyczyną), sprawdzenie pierwszej poprawki na tymczasowej gałęzi i końcowy zielony przebieg opisany wyżej.

### 1. Przebieg 44477002456 — błąd środowiska runnera (failure)

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

### 2. Przebieg 44477934521 — sprawdzenie poprawki na tymczasowej gałęzi (success)

Potwierdzenie poprawki z punktu 1 na GitHubie bez zmiany gałęzi delivery: tymczasowa gałąź `ci-check/faza-3-ops` (drzewo różniące się od commita dowodów tylko plikiem `ci.md`), draft PR [#4](https://github.com/l3x1cn/patchpoint/pull/4), przebieg https://github.com/l3x1cn/patchpoint/actions/runs/44477934521 (commit `2d9948e86b2c2b42d3de35c926cab76ebb94f778`, zdarzenie `pull_request`, 2026-11-19) zakończony wynikiem `success`. Po sprawdzeniu PR #4 zamknięto, a gałąź usunięto; wystarczyła jedna próba z trzech dopuszczalnych.

| Job | Wynik | Czas |
|---|---|---|
| `quality` | `success` | 0 min 57 s |
| `semgrep` | `success` | 0 min 34 s |
| `trivy-fs` | `success` | 0 min 25 s |
| `ansible` | `success` | 0 min 32 s |
| `build` | `success` | 1 min 21 s |
| `publish` | `skipped` | 0 min 0 s |

Artefakty tego przebiegu: `semgrep` 116497 B, `trivy-fs` 2222 B, `build-reports` 83796 B, `images` 88479228 B.

### 3. Przebieg 44519720743 — nowa podatność w bazie Trivy (failure)

Przebieg na `delivery/faza-3-ops` (https://github.com/l3x1cn/patchpoint/actions/runs/44519720743, commit `5d56c56b52112073a614a1e186c8966402f2deed`, zdarzenie `pull_request`, 2026-11-19, utworzony 11:59:33 UTC) zakończył się wynikiem `failure`:

| Job | Wynik | Czas |
|---|---|---|
| `quality` | `success` | 0 min 54 s |
| `semgrep` | `success` | 0 min 39 s |
| `trivy-fs` | `success` | 0 min 33 s |
| `ansible` | `success` | 0 min 25 s |
| `build` | `failure` | 0 min 44 s |
| `publish` | `skipped` | 0 min 0 s |

- Przyczyna: w jobie `build` krok „Bramka Trivy (obrazy)” zwrócił kod 2, zgodnie z projektem bramki. W bazie podatności Trivy pojawiła się nowa podatność HIGH CVE-2026-118899 w nginx 1.30.6-r1 w obrazie proxy; poprawka jest w nginx 1.30.7-r0, której nie ma jeszcze w żadnym tagu obrazu `owasp/modsecurity-crs`. Kroki smoke i eksportu obrazów zostały pominięte, a `publish` nie wystartował. Lokalne skany z rana tego samego dnia jeszcze jej nie widziały.
- Rozstrzygnięcie: wygasający wyjątek w `.trivyignore` (`exp:2026-12-19`) przyjęty przez zespół jako ryzyko do wydania tagu obrazu CRS z nginx 1.30.7-r0; wiersz w [`triaz-skanow.md`](triaz-skanow.md) i opis w sekcji 13 raportu Fazy 3. Poprawka w commicie `26d93eb`.
- Wynik: przebieg 44520467614 na commicie `26d93eb` (tabele „Przebieg”, „Joby” i „Artefakty” wyżej) zakończył się wynikiem `success`.
