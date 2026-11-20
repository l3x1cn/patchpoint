# Raport Architektoniczny DevSecOps — PatchPoint

Raport zbiorczy projektu realizowanego w kursie „AI-Driven DevSecOps”, Scenariusz 5: Menadżer Zadań IT (IT Ticketing System). Projekt przeszedł trzy fazy z rolami Dev, Sec i Ops, a AI uczestniczyło w każdej z nich (generowanie kodu, audyt Red Team, poprawki, kontenery, potok CI/CD i wdrożenie). Raport łączy Sekcję Sec (Faza 2) i Sekcję Ops (Faza 3); szczegóły są w raportach faz.

## 1. Elementy zaliczeniowe

| Element (instrukcja kursu) | Gdzie w repozytorium | Dowód |
|---|---|---|
| Działający, bezpieczny kod aplikacji | `backend/` (FastAPI, SQLite), `frontend/` (HTML/JS) | [raport Fazy 2](faza-2-sec/README.md), [dowody Fazy 2](faza-2-sec/dowody/README.md) |
| Bezpieczny Dockerfile (least privilege) | `backend/Dockerfile` (API), `deploy/proxy/Dockerfile` (proxy z WAF) | [sekcja 5 raportu Fazy 3](faza-3-ops/README.md#5-bezpieczne-obrazy-kontenerów), [`obrazy.txt`](faza-3-ops/dowody/obrazy.txt), [`trivy-obrazy.txt`](faza-3-ops/dowody/trivy-obrazy.txt) |
| Pipeline CI/CD (`.yaml`) | `.github/workflows/ci.yml` | [sekcja 8 raportu Fazy 3](faza-3-ops/README.md#8-potok-cicd), [`ci.md`](faza-3-ops/dowody/ci.md) |
| Raport Architektoniczny DevSecOps | ten dokument: sekcja 3 (Sec) i sekcja 4 (Ops) | raporty [Fazy 2](faza-2-sec/README.md) i [Fazy 3](faza-3-ops/README.md) |

## 2. System w skrócie

PatchPoint to system wsparcia technicznego, w którym pracownicy zgłaszają awarie sprzętu IT do działu Helpdesk. Backend (Python, FastAPI, SQLite) i minimalny frontend (HTML/JS) działają lokalnie na dwóch originach; w środowisku docelowym jeden kontener reverse proxy (nginx z ModSecurity i OWASP CRS) kończy TLS, serwuje statyczny UI i przekazuje `/api/` do kontenera API w sieci bez wyjścia do Internetu, więc UI i API leżą pod jednym originem. Architekturę i API w stanie z Fazy 1 opisuje [raport Fazy 1](faza-1-dev/README.md), a architekturę produkcyjną — [sekcja 4 raportu Fazy 3](faza-3-ops/README.md#4-logiczna-architektura-sieci).

## 3. Sekcja Sec

Audyt AI („Wirtualny Red Teamer”) objął 18 słabości z rejestru Fazy 1 i dał 16 znalezisk, a wszystkie 18 pozycji rejestru zostało trafionych. Skrypt PoC `scripts/security_check.sh` zwracał 22 × `[PODATNE]` na kodzie Fazy 1 i zwraca 22 × `[NAPRAWIONE]` na kodzie Fazy 2 (także w kontenerze API w Fazie 3). Pełne zestawienie luk, mechanizmów naprawy i testów regresyjnych: sekcja 4 [raportu Fazy 2](faza-2-sec/README.md).

| Wektor ataku | Luki z Fazy 1 | Mechanizmy naprawy | Szczegóły |
|---|---|---|---|
| Information Disclosure | gadatliwe błędy bazy i komunikat UNIQUE (W-01, W-02), debug i `/docs` (W-03), health z wersjami (W-04), hash hasła w API (W-06), SQL injection w wyszukiwaniu (W-14), odczyt cudzych zgłoszeń (W-16), `OverflowError` dla dużych identyfikatorów | parametryzowane zapytanie z `ESCAPE`; ogólny 500 z `error_id` (szczegóły tylko w logu); kontrola własności zgłoszenia (404 dla cudzych); `{"status": "ok"}` w health; dokumentacja API domyślnie wyłączona; odpowiedzi bez hasha; identyfikatory w zakresie 1…2⁶³−1 | [raport Fazy 2](faza-2-sec/README.md), sekcje 4–6; [threat model](faza-2-sec/threat-model.md) |
| Broken Authentication | enumeracja kont (W-05), MD5 i przewidywalny token (W-07, W-08), brak wygasania sesji i wylogowania (W-09, W-10), słabe flagi ciasteczka, token w JSON i `Bearer` (W-11), konta domyślne, słabe hasła i brak limitu prób (W-12), mass assignment roli (W-15), XSS z kradzieżą ciasteczka (W-17), brak logów zdarzeń (W-18) | Argon2id i polityka haseł 15–128 znaków; token `secrets.token_urlsafe(32)` z samym SHA-256 w bazie; sesja 30 minut bezczynności i 8 godzin; ciasteczko `HttpOnly; Secure; SameSite=Strict`; jednolite 401 i blokada 5 prób w 15 minut; rola zawsze `employee`; DOM przez `textContent` i CSP; zdarzenia JSON w `patchpoint.security` | [raport Fazy 2](faza-2-sec/README.md), sekcje 4–6 |
| CORS | `allow_origins=["*"]` z poświadczeniami (W-13) | lista originów z `PATCHPOINT_CORS_ORIGINS` bez `*`; metody GET/POST/PATCH i nagłówek `Content-Type`; `OriginCheckMiddleware` (403 dla obcego `Origin`); `SameSite=Strict`; w produkcji jeden origin za proxy | [raport Fazy 2](faza-2-sec/README.md), sekcje 4–6; [sekcja 6 raportu Fazy 3](faza-3-ops/README.md#6-brzeg-sieci-tls-waf-i-limit-żądań) |

## 4. Sekcja Ops

Pełny opis: [raport Fazy 3](faza-3-ops/README.md).

1. **Środowisko.** Jeden serwer VPS u dostawcy (IaaS) z domeną i Let's Encrypt, Docker Engine z Compose, obrazy z GHCR: [sekcja 3](faza-3-ops/README.md#3-środowisko-docelowe).
2. **Strefy sieci.** Zapora hosta (nftables), publiczna sieć `edge` z proxy i prywatna sieć `backend` (`internal`) z API i bazą; porty 80 i 443 na zewnątrz, SSH tylko kluczem, ze źródeł zawężanych w inventory (domyślnie cały Internet): [sekcja 4](faza-3-ops/README.md#4-logiczna-architektura-sieci).
3. **WAF i TLS.** ModSecurity z OWASP CRS 4.30.0 w trybie blokującym, TLS 1.2/1.3, HSTS, nagłówki UI, limit żądań dla logowania i rejestracji, nadpisany `X-Forwarded-For` i `__Host-session`: [sekcja 6](faza-3-ops/README.md#6-brzeg-sieci-tls-waf-i-limit-żądań).
4. **Zmienne i sekrety.** Zmienne stosu z `compose.yaml` i `.env` z Ansible; sekrety w Ansible Vault i plikach 0600, nigdy w repozytorium ani obrazie: [sekcja 7](faza-3-ops/README.md#7-zmienne-środowiskowe-i-sekrety).
5. **CI/CD.** GitHub Actions: testy, Semgrep, Trivy i ansible-lint przed budową obrazów, bramka Trivy obrazów, smoke stosu i publikacja w GHCR po pushu na `main`: [sekcja 8](faza-3-ops/README.md#8-potok-cicd).
6. **Infrastruktura jako kod.** Ansible (role `base`, `docker`, `patchpoint`, `letsencrypt`): [sekcja 9](faza-3-ops/README.md#9-wdrożenie-i-infrastruktura-jako-kod-ansible).

Odpowiedniki rozwiązania w chmurze publicznej (AWS): [Aneks A](faza-3-ops/README.md#aneks-a-odpowiedniki-w-chmurze-publicznej-aws).

## 5. Dowody

- [Dowody Fazy 2](faza-2-sec/dowody/README.md): audyt, PoC przed i po naprawie, testy, demo, zdarzenia bezpieczeństwa.
- [Dowody Fazy 3](faza-3-ops/dowody/README.md): jakość, testy, skanery z triażem, obrazy, smoke stosu, ansible-lint, przebieg CI.

## 6. Ryzyka rezydualne

- Faza 2: [sekcja 9 raportu Fazy 2](faza-2-sec/README.md) (ryzyka rezydualne i przekazanie do Fazy 3).
- Faza 3: [sekcja 13 raportu Fazy 3](faza-3-ops/README.md#13-ryzyka-rezydualne); stan realizacji przekazania z Fazy 2: [sekcja 11](faza-3-ops/README.md#11-realizacja-przekazania-z-fazy-2).
