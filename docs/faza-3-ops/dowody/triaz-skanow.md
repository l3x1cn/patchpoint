# Triaż skanerów bezpieczeństwa — Faza 3

Stan z 2026-11-19 po zadaniu 3 planu Fazy 3. Skanery: Semgrep 1.185.0 z zestawami reguł `p/python`, `p/javascript`, `p/dockerfile`, `p/docker-compose`, `p/github-actions` i `p/owasp-top-ten` (`SEMGREP_CONFIGS` w `scripts/scan.sh`) oraz Trivy 0.76.2 z bazą podatności z dnia skanu. Polecenia: `make semgrep`, `make trivy-fs` i `make trivy-images` (całość: `make scan`). Bramki są te same lokalnie i w CI.

Zasady rozstrzygania znalezisk:

1. Podatność HIGH lub CRITICAL z poprawką w `backend/uv.lock`: podniesienie pakietu (`uv lock --upgrade-package`), testy i ponowny skan.
2. Podatność w obrazie API: przebudowa bez cache (`apt-get upgrade`), potem nowszy digest obrazu bazowego, na końcu wpis w `.trivyignore`.
3. Podatność w obrazie proxy: najnowszy tag `owasp/modsecurity-crs:4.30.0-nginx-alpine-<data>`, na końcu wpis w `.trivyignore` (bez `apk upgrade`, bo moduł ModSecurity jest zbudowany dla konkretnej wersji nginx).
4. Błąd konfiguracji HIGH lub CRITICAL w Dockerfile: poprawka Dockerfile.
5. Sekret w śledzonym pliku: zatrzymanie zadania i decyzja o rotacji po stronie zespołu.
6. Semgrep w plikach zadań 1–2 i w `frontend/**`: poprawka w miejscu znaleziska; fałszywie dodatnie wynik dostaje komentarz `nosemgrep: <id reguły>` z uzasadnieniem linię wyżej.
7. Semgrep w `backend/app/**`: bez zmian w kodzie w zadaniu 3; decyzja „do zadania 4”.

Wpisy w `.trivyignore` wygasają po najwyżej 30 dniach (`exp:`), po czym Trivy znów zgłasza znalezisko.

Pierwszy skan: Semgrep 3 znaleziska, Trivy fs 3 znaleziska CRITICAL (konfiguracja Dockerfile), Trivy obrazy 5 znalezisk HIGH z poprawką (obraz proxy; obraz API bez znalezisk). Plik `backend/uv.lock` nie ma podatności, skaner sekretów nie znalazł nic.

| Narzędzie | Znalezisko (reguła albo CVE) | Plik i linia albo pakiet | Poziom | Decyzja | Uzasadnienie albo poprawka | Zadanie |
|---|---|---|---|---|---|---|
| Semgrep | `generic.nginx.security.request-host-used.request-host-used` | `deploy/proxy/templates/conf.d/default.conf.template:2` | WARNING (blokujące) | naprawione | Znalezisko dotyczyło komentarza z nazwą zmiennej nginx; komentarz przeformułowany z przykładami zmiennych, które nie uruchamiają reguły (`$uri`, `$request_uri`). | 3 |
| Semgrep | `generic.nginx.security.request-host-used.request-host-used` | `deploy/proxy/templates/conf.d/default.conf.template:26` | WARNING (blokujące) | naprawione | Przekierowanie 301 na HTTPS używało nagłówka Host od klienta; teraz używa stałej nazwy serwera `${SERVER_NAME}`, więc komentarz `nosemgrep` został usunięty. | 3 |
| Semgrep | `generic.nginx.security.request-host-used.request-host-used` | `deploy/proxy/templates/includes/patchpoint-proxy.conf.template:10` | WARNING (blokujące) | naprawione | Do API trafiał nagłówek Host od klienta, a przekierowania Starlette (`redirect_slashes`, 307) odbijają go w `Location`. Proxy przekazuje teraz stałą nazwę serwera (`proxy_set_header Host ${SERVER_NAME}`), więc Host od klienta nie dociera do API. | 3 |
| Trivy fs | DS-0031 (`Possible exposure of secret env "SSL_CERT_KEY_FILE"`) | `deploy/proxy/Dockerfile:25` (instrukcja `ENV`) | CRITICAL | wyjątek: fałszywie dodatnie | Heurystyka bierze nazwę z `KEY` za sekret; wartość to ścieżka do pliku klucza montowanego z hosta, a klucz nie trafia do obrazu. Nazwy zmiennej narzuca obraz bazowy. Zmienna przeniesiona do osobnej instrukcji `ENV` z `# trivy:ignore:DS-0031`, żeby wyjątek nie obejmował pozostałych zmiennych. | 3 |
| Trivy fs | DS-0031 (`Possible exposure of secret env "PATCHPOINT_AUTH_RATE"`) | `deploy/proxy/Dockerfile:25` (instrukcja `ENV`) | CRITICAL | wyjątek: fałszywie dodatnie | Heurystyka bierze nazwę z `AUTH` za sekret; wartość `10r/m` to limit żądań. Ta sama osobna instrukcja `ENV` z `# trivy:ignore:DS-0031`. | 3 |
| Trivy fs | DS-0031 (`Possible exposure of secret env "PATCHPOINT_AUTH_BURST"`) | `deploy/proxy/Dockerfile:25` (instrukcja `ENV`) | CRITICAL | wyjątek: fałszywie dodatnie | Jak wyżej; wartość `5` to rozmiar serii limitu żądań. | 3 |
| Trivy obrazy | CVE-2026-113425 | `nginx` 1.30.6-r1 w obrazie proxy | HIGH | naprawione: podbicie obrazu (wyjątek usunięty 2026-11-27) | Poprawka w nginx 1.30.7-r0, którego 2026-11-19 nie było w żadnym tagu CRS; do tego czasu wyjątek do 2026-12-19 (dotyczył proxy poczty, którego konfiguracja nie używa). Tag `4.30.0-nginx-alpine-202611271111` ma nginx 1.30.8-r1. | 3 |
| Trivy obrazy | CVE-2026-121810 | `nginx` 1.30.6-r1 w obrazie proxy | HIGH | naprawione: podbicie obrazu (wyjątek usunięty 2026-11-27) | Jak wyżej. Dotyczyło HTTP/3 (QUIC); konfiguracja nie ma nasłuchu quic. | 3 |
| Trivy obrazy | CVE-2026-123007 | `nginx` 1.30.6-r1 w obrazie proxy | HIGH | naprawione: podbicie obrazu (wyjątek usunięty 2026-11-27) | Jak wyżej. Dotyczyło HTTP/2; obraz ustawia `HTTP2=off` (`deploy/proxy/Dockerfile`), więc warunek nie był spełniony. | 3 |
| Trivy obrazy | CVE-2026-123633 | `nginx` 1.30.6-r1 w obrazie proxy | HIGH | naprawione: podbicie obrazu (wyjątek usunięty 2026-11-27) | Jak wyżej. Dotyczyło HTTP/2; `HTTP2=off`, więc warunek nie był spełniony. | 3 |
| Trivy obrazy | CVE-2026-123634 | `nginx` 1.30.6-r1 w obrazie proxy | HIGH | naprawione: podbicie obrazu (wyjątek usunięty 2026-11-27) | Jak wyżej. Wymagało `proxy_pass` ze zmienną oraz `ssi` albo `mirror`; `nginx -T` nie pokazywał `ssi` ani `mirror`, więc warunek nie był spełniony. | 3 |
| Trivy obrazy | CVE-2026-118899 | `nginx` 1.30.6-r1 w obrazie proxy | HIGH | naprawione: podbicie obrazu (wyjątek usunięty 2026-11-27) | Dotyczyło tej konfiguracji: przy `listen ... ssl` i TLS 1.3 spreparowane połączenie TLS mogło wprowadzić proces roboczy nginx w nieskończoną pętlę (zdalny DoS bez uwierzytelnienia, tylko warstwa danych). Do 2026-11-27 było to świadomie przyjęte ryzyko dostępności (UID 101, `cap_drop: ALL`, `no-new-privileges`; `restart: unless-stopped` nie wyprowadza kontenera z pętli, ręczny `docker compose restart proxy`). Tag `4.30.0-nginx-alpine-202611271111` ma nginx 1.30.8-r1 z poprawką (od 1.30.7). | CI |
| Trivy obrazy | CVE-2026-124851 | `libzstd1` 1.5.7+dfsg-1 w lokalnym obrazie API | HIGH | naprawione: przebudowa bez cache | Skan z 2026-11-27 zgłosił podatność w obrazie zbudowanym z lokalnej warstwy cache (`apt-get upgrade` z poprzedniej budowy). Poprawka `1.5.7+dfsg-1+deb13u1` jest w repozytorium Debiana, ale nie w obrazach bazowych (`python:3.14.10-slim`, `python:3.15.1-slim`, `debian:trixie-slim`). `docker build --no-cache` uruchamia `apt-get upgrade` od nowa, instaluje poprawioną wersję i Trivy nie zgłasza znalezisk (Debian 13.8). Wyjątek w `.trivyignore` nie był potrzebny. Budowa w CI nie używa cache warstw. | 2026-11-27 |

Uwagi:

- Wpisy `.trivyignore` dla nginx 1.30.6 (CVE-2026-113425, CVE-2026-121810, CVE-2026-123007, CVE-2026-123633, CVE-2026-123634, CVE-2026-118899) wygasały 2026-12-19; usunięto je 2026-11-27 po podbiciu obrazu proxy do tagu `4.30.0-nginx-alpine-202611271111` (nginx 1.30.8-r1, digest `sha256:e473af8dcd3ef1ecb9ad61622c0a1dc82a61b3db7844fdd500de228244e0e25f`). Baza Trivy opublikowała pierwsze pięć CVE 2026-11-18, więc obraz z 2026-11-16 nie mógł ich uwzględnić.
- Baza podatności zmieniła się między skanami lokalnymi (rano 2026-11-19, pięć CVE nginx) a przebiegiem CI na końcowym stanie gałęzi (przebieg `44519720743`): pojawiło się CVE-2026-118899 (HIGH, nginx 1.30.6-r1, poprawka w 1.30.7-r0, której nadal nie ma w żadnym tagu obrazu CRS; najnowszy to `4.30.0-nginx-alpine-202611160811`), więc bramka Trivy obrazów w jobie `build` zawiodła. Ponieważ tej luki nie wyklucza konfiguracja (nasłuch TLS z TLS 1.3 jest potrzebny), zespół przyjął ryzyko wyjątkiem z datą przeglądu 2026-12-19, tak jak pozostałe wpisy; dla tego CVE jest to jedyny wyjątek z realnie spełnionym warunkiem wykorzystania.
- Semgrep zgłaszał błąd składni (`Syntax error`, poziom ostrzeżenia, nie znalezisko) przy parsowaniu `scripts/security_check.sh`: nawiasy wewnątrz `${DB_PATH:+...}` wywalają parser bash. Poprawiono 2026-11-27 (szczegóły w zmiennej), a `scripts/scan.sh semgrep` kończy się teraz porażką przy każdym `Syntax error`.
- Pominięte ścieżki (`.semgrepignore`): `docs/`, `backend/tests/`, katalogi narzędzi i `deploy/proxy/dev-tls/`.

Podsumowanie po zadaniu 3: Semgrep 0 znalezisk, Trivy fs 0 HIGH/CRITICAL, Trivy obrazy 0 HIGH/CRITICAL z poprawką.

Podsumowanie po zadaniu 5: Semgrep 0 znalezisk (po dodaniu `compose.yaml` i `scripts/stack_smoke.sh`; reguła `writable-filesystem-service` nie zgłosiła proxy, więc bez wyjątku `nosemgrep`), Trivy fs 0 HIGH/CRITICAL, Trivy obrazy 0 HIGH/CRITICAL z poprawką.

Podsumowanie po zadaniu 6: Semgrep 0 znalezisk (po dodaniu `deploy/ansible/`; zestawy z `SEMGREP_CONFIGS` nie zawierają reguł dla Ansible, a poprawność playbooka sprawdza `make ansible-lint`), Trivy fs 0 HIGH/CRITICAL, bez nowych wyjątków w `.trivyignore`.

Podsumowanie po zadaniu 7: Semgrep 0 znalezisk (po dodaniu `.github/workflows/ci.yml` i `.github/dependabot.yml`; zestaw `p/github-actions` nie zgłosił nic, bez wyjątków dla `ci.yml`), Trivy fs 0 HIGH/CRITICAL, Trivy obrazy 0 HIGH/CRITICAL z poprawką, bez nowych wpisów w `.trivyignore`.

Podsumowanie końcowe (zadanie 9): Semgrep 0 znalezisk (275 reguł na 71 plikach, [`semgrep.txt`](semgrep.txt)), Trivy fs 0 HIGH/CRITICAL ([`trivy-fs.txt`](trivy-fs.txt)), Trivy obrazy 0 HIGH/CRITICAL z poprawką ([`trivy-obrazy.txt`](trivy-obrazy.txt); obraz API: Debian 13.7, obraz proxy: Alpine 3.24.4). W `.trivyignore` pozostaje sześć wpisów dla nginx (CVE-2026-113425, CVE-2026-121810, CVE-2026-123007, CVE-2026-123633, CVE-2026-123634 i CVE-2026-118899) z datą przeglądu 2026-12-19; pięć z nich dotyczy funkcji, których konfiguracja nie używa, a CVE-2026-118899 (DoS przez TLS 1.3) dotyczy proxy i jest przyjętym ryzykiem; wyjątek `trivy:ignore` bez zmian względem zadania 3, a wyjątek `nosemgrep` z zadania 3 usunięty (przekierowanie 301 używa stałej nazwy serwera), więc w repozytorium nie ma już komentarzy `nosemgrep`.

Podsumowanie po sprzątaniu (2026-11-27): Semgrep 0 znalezisk i 0 błędów składni, ShellCheck i actionlint bez uwag (`make shellcheck`, `make actionlint`, job `scripts` w CI), Trivy fs i Trivy obrazów 0 HIGH/CRITICAL z poprawką, `.trivyignore` bez aktywnych wpisów (obraz API: Debian 13.8, obraz proxy: Alpine 3.24.4 z nginx 1.30.8).
