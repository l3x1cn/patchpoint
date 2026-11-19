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
| Semgrep | `generic.nginx.security.request-host-used.request-host-used` | `deploy/proxy/templates/conf.d/default.conf.template:26` | WARNING (blokujące) | wyjątek: fałszywie dodatnie | Przekierowanie 301 na HTTPS używa hosta z tego samego żądania; przeglądarka nie pozwala cudzej witrynie ustawić nagłówka Host, a stała nazwa zepsułaby wejście przez adres IP (smoke, lokalny stos). Komentarz `nosemgrep` w linii znaleziska. | 3 |
| Semgrep | `generic.nginx.security.request-host-used.request-host-used` | `deploy/proxy/templates/includes/patchpoint-proxy.conf.template:10` | WARNING (blokujące) | naprawione | Do API trafiał nagłówek Host od klienta, a przekierowania Starlette (`redirect_slashes`, 307) odbijają go w `Location`. Proxy przekazuje teraz stałą nazwę serwera (`proxy_set_header Host ${SERVER_NAME}`), więc Host od klienta nie dociera do API. | 3 |
| Trivy fs | DS-0031 (`Possible exposure of secret env "SSL_CERT_KEY_FILE"`) | `deploy/proxy/Dockerfile:25` (instrukcja `ENV`) | CRITICAL | wyjątek: fałszywie dodatnie | Heurystyka bierze nazwę z `KEY` za sekret; wartość to ścieżka do pliku klucza montowanego z hosta, a klucz nie trafia do obrazu. Nazwy zmiennej narzuca obraz bazowy. Zmienna przeniesiona do osobnej instrukcji `ENV` z `# trivy:ignore:DS-0031`, żeby wyjątek nie obejmował pozostałych zmiennych. | 3 |
| Trivy fs | DS-0031 (`Possible exposure of secret env "PATCHPOINT_AUTH_RATE"`) | `deploy/proxy/Dockerfile:25` (instrukcja `ENV`) | CRITICAL | wyjątek: fałszywie dodatnie | Heurystyka bierze nazwę z `AUTH` za sekret; wartość `10r/m` to limit żądań. Ta sama osobna instrukcja `ENV` z `# trivy:ignore:DS-0031`. | 3 |
| Trivy fs | DS-0031 (`Possible exposure of secret env "PATCHPOINT_AUTH_BURST"`) | `deploy/proxy/Dockerfile:25` (instrukcja `ENV`) | CRITICAL | wyjątek: fałszywie dodatnie | Jak wyżej; wartość `5` to rozmiar serii limitu żądań. | 3 |
| Trivy obrazy | CVE-2026-113425 | `nginx` 1.30.6-r1 w obrazie proxy | HIGH | wyjątek: brak poprawki (exp 2026-12-19) | Poprawka w nginx 1.30.7-r0; najnowszy tag obrazu CRS (`4.30.0-nginx-alpine-202611160811`) jej jeszcze nie zawiera. Dotyczy proxy poczty, którego konfiguracja nie używa. | 3 |
| Trivy obrazy | CVE-2026-121810 | `nginx` 1.30.6-r1 w obrazie proxy | HIGH | wyjątek: brak poprawki (exp 2026-12-19) | Jak wyżej. Dotyczy HTTP/3 (QUIC); konfiguracja nie ma nasłuchu quic. | 3 |
| Trivy obrazy | CVE-2026-123007 | `nginx` 1.30.6-r1 w obrazie proxy | HIGH | wyjątek: brak poprawki (exp 2026-12-19) | Jak wyżej. Dotyczy HTTP/2; obraz ustawia `HTTP2=off` (`deploy/proxy/Dockerfile`), więc nginx nie negocjuje h2 (ALPN) ani nie przyjmuje h2c — warunek nie jest spełniony. | 3 |
| Trivy obrazy | CVE-2026-123633 | `nginx` 1.30.6-r1 w obrazie proxy | HIGH | wyjątek: brak poprawki (exp 2026-12-19) | Jak wyżej. Dotyczy HTTP/2; obraz ustawia `HTTP2=off` (`deploy/proxy/Dockerfile`), więc nginx nie negocjuje h2 (ALPN) ani nie przyjmuje h2c — warunek nie jest spełniony. | 3 |
| Trivy obrazy | CVE-2026-123634 | `nginx` 1.30.6-r1 w obrazie proxy | HIGH | wyjątek: brak poprawki (exp 2026-12-19) | Jak wyżej. Wymaga `proxy_pass` ze zmienną oraz dyrektywy `ssi` albo `mirror`; proxy używa zmiennej, ale `nginx -T` w obrazie nie pokazuje `ssi` ani `mirror`, więc warunek nie jest spełniony. | 3 |

Uwagi:

- Wpisy CVE-2026-113425, CVE-2026-121810, CVE-2026-123007, CVE-2026-123633 i CVE-2026-123634 w `.trivyignore` wygasają 2026-12-19. Do tej daty trzeba podnieść obraz proxy do tagu z nginx 1.30.7-r0 albo przedłużyć wpisy z nowym uzasadnieniem. Baza Trivy opublikowała te CVE 2026-11-18, więc obraz z 2026-11-16 nie mógł ich uwzględnić.
- Semgrep zgłasza błąd składni (`Syntax error`, poziom ostrzeżenia, nie znalezisko) przy parsowaniu `scripts/security_check.sh`; plik jest skanowany pozostałymi regułami i bramka nie jest tym blokowana.
- Pominięte ścieżki (`.semgrepignore`): `docs/`, `backend/tests/`, katalogi narzędzi i `deploy/proxy/dev-tls/`.

Podsumowanie po zadaniu 3: Semgrep 0 znalezisk, Trivy fs 0 HIGH/CRITICAL, Trivy obrazy 0 HIGH/CRITICAL z poprawką.

Podsumowanie po zadaniu 5: Semgrep 0 znalezisk (po dodaniu `compose.yaml` i `scripts/stack_smoke.sh`; reguła `writable-filesystem-service` nie zgłosiła proxy, więc bez wyjątku `nosemgrep`), Trivy fs 0 HIGH/CRITICAL, Trivy obrazy 0 HIGH/CRITICAL z poprawką.

Podsumowanie po zadaniu 6: Semgrep 0 znalezisk (po dodaniu `deploy/ansible/`; zestawy z `SEMGREP_CONFIGS` nie zawierają reguł dla Ansible, a poprawność playbooka sprawdza `make ansible-lint`), Trivy fs 0 HIGH/CRITICAL, bez nowych wyjątków w `.trivyignore`.
