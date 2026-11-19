# Dziennik promptów AI — Faza 3 (OPS)

## 1. Narzędzia

Użyto Claude (Anthropic) uruchomionego w harnessie omp. Tryb planowania obejmował:

- analizę repozytorium i środowiska;
- sprawdzenie obrazów (`docker buildx imagetools inspect`), SHA akcji (`gh api`), wersji (PyPI, Galaxy) i obrazu CRS; do dwóch z tych zadań użyto agentów `scout` (obraz `owasp/modsecurity-crs`, wersje narzędzi CI);
- pytania doprecyzowujące do zespołu;
- plan.

Realizację prowadziła wtyczka delivery:

- zadanie 4 wykonał agent `python-developer:developer` (TDD, ruff, mypy);
- zadania 1–3 i 5–9 wykonał `delivery:implementer`;
- każdy wynik przed commitem przeglądał `delivery:task-reviewer`;
- po zadaniach przewidziano weryfikację z planu, QA i końcowy code review; ich wyniki powstają po tym dokumencie, w osobnych raportach (`docs/testing/reports/`, `docs/reviews/`).

## 2. Prompt nr 1 (zespół → AI)

Treść dosłownie, wraz z brakiem polskich znaków. Instrukcja kursu i scenariusz, na których opiera się Faza 3, były w prompcie nr 1 Fazy 1 ([`../faza-1-dev/prompty.md`](../faza-1-dev/prompty.md), sekcja 2); w Fazie 3 zespół użył jednego krótkiego polecenia w trybie planowania:

```text
przygotuj plan implementacyjny fazy 3
```

## 3. Pytania doprecyzowujące AI i odpowiedzi zespołu

Odpowiedzi dosłownie, wraz z brakiem polskich znaków.

| Runda | Pytanie AI | Odpowiedź zespołu |
|---|---|---|
| 1 | Którą chmurę opisać w Sekcji Ops (architektura sieci, WAF, sekrety)? | projekt bedzie hostowany na wlasnym serverze |
| 1 | Jaką topologię kontenerów zbudować? | API + reverse proxy (jeden origin) |
| 1 | Jak daleko ma sięgać potok GitHub Actions? | Skan, budowa, smoke, publikacja w GHCR |
| 1 | Które dodatkowe wzmocnienia włączyć? (można nic) | Limit per IP w nginx; Prefiks __Host- ciasteczka; IaC sieci (OpenTofu) |
| 1 | Brakuje lokalnie docker compose. Jak weryfikować stos lokalnie? | Zainstaluję docker-compose |
| 2 | Jaki to serwer? | VPS/dedyk u dostawcy |
| 2 | Jak użytkownicy mają docierać do aplikacji i kto kończy TLS? | Domena + Let's Encrypt |
| 2 | Jak zrealizować WAF? | ModSecurity + OWASP CRS w proxy |
| 2 | Co ma być infrastrukturą jako kod przy własnym serwerze? | Ansible |
| 2 | Dodać do Sekcji Ops aneks z odpowiednikami w chmurze publicznej (AWS: VPC, ALB+WAF, ECS, Secrets Manager), żeby spełnić dosłowne „w chmurze” z instrukcji? | Tak, krótki aneks |
| 3 | Czy weryfikacja planu może wypchnąć gałąź delivery/faza-3-ops i otworzyć draft PR, żeby uruchomić potok CI i zapisać wynik w dowodach? | Tak, push + draft PR |

Odpowiedź o hostingu na własnym serwerze doprowadziła do rundy 2. Ansible zastąpił wybrane w rundzie 1 OpenTofu, bo infrastruktura jako kod dla sieci typu VPC nie pasuje do pojedynczego serwera.

## 4. Prompt nr 2 — plan wygenerowany przez AI

Drugim „promptem” jest plan wygenerowany przez AI na podstawie polecenia z punktu 2 i odpowiedzi z punktu 3: dziewięć zadań z opisem zmian, wartościami przypiętych wersji i kryteriami „Gotowe, gdy”. Plan znajduje się w pliku [`docs/plans/2026-11-18-faza-3-ops.md`](../plans/2026-11-18-faza-3-ops.md). Definicję potoku CI/CD (`.github/workflows/ci.yml`) wygenerowała AI: najpierw w planie, potem przez agenta w zadaniu 7.

## 5. Prompty nr 3–11 — zadania 1–9 przekazane agentom

Treść każdego zadania z planu (od „Task 1” do „Task 9”) została przekazana agentowi realizującemu w jednolitym szablonie delivery; w miejsce `<TASK_BLOCK>` wstawiany jest pełny blok zadania z planu:

```text
You are implementing Task <N> of the plan <PLAN_PATH>.

<TASK_BLOCK>

Rules:
- Implement exactly this task. Write tests first when the task lists a Test file.
- Do not commit, stash, switch branches or rewrite history. Leave all changes in the working tree.
- End with your report, including a **Status:** line (✅ Complete | ⚠️ Partial | ❌ Failed).
```

| Prompt | Zadanie |
|---|---|
| nr 3 | Zadanie 1 — obraz kontenera API (multi-stage, rootless, slim) |
| nr 4 | Zadanie 2 — obraz reverse proxy z WAF, TLS i statycznym UI |
| nr 5 | Zadanie 3 — bramki skanerów Semgrep i Trivy oraz triaż |
| nr 6 | Zadanie 4 — backend: konfigurowalna nazwa ciasteczka sesji (prefiks `__Host-`) |
| nr 7 | Zadanie 5 — stos compose, smoke obrazów i stosu, konfiguracja QA |
| nr 8 | Zadanie 6 — Ansible: utwardzenie VPS i wdrożenie stosu |
| nr 9 | Zadanie 7 — potok CI/CD GitHub Actions i Dependabot |
| nr 10 | Zadanie 8 — push gałęzi, draft PR i dowód przebiegu CI |
| nr 11 | Zadanie 9 — dokumentacja Fazy 3: Sekcja Ops, raport DevSecOps, dziennik promptów i dowody |

Zadanie 9 dostało od orkiestratora dodatkowe wskazówki o odstępstwach wykonania od planu; opisuje je sekcja 7.

## 6. Zadanie → agent → commit

Commity zadań 1–8 pochodzą z polecenia `git log --format='%h %s%n%b' --grep='Delivery-Task:'`. Rundy poprawek to kolejne przejścia agenta po uwagach `delivery:task-reviewer` przed commitem; liczby pochodzą z raportów orkiestratora delivery (treść uwag nie jest zapisana w repozytorium).

| Zadanie | Tytuł | Agent | Commit | Rundy poprawek |
|---|---|---|---|---|
| 1 | Obraz kontenera API (multi-stage, rootless, slim) | `delivery:implementer` | `0184b8a` build(backend): add hardened multi-stage API image | 0 |
| 2 | Obraz reverse proxy z WAF, TLS i statycznym UI | `delivery:implementer` | `1e82366` build(proxy): add reverse proxy image with ModSecurity CRS, TLS and UI | 0 |
| 3 | Bramki skanerów Semgrep i Trivy oraz triaż | `delivery:implementer` | `cc58939` chore(scripts): add Semgrep and Trivy scan gates | 1 |
| 4 | Backend — konfigurowalna nazwa ciasteczka sesji (prefiks `__Host-`) | `python-developer:developer` | `225421f` feat(backend): make the session cookie name configurable for the __Host- prefix | 0 |
| 5 | Stos compose, smoke obrazów i stosu, konfiguracja QA | `delivery:implementer` | `4a06b7e` feat(deploy): add compose stack, stack smoke test and QA targets | 0 (przyjęte drobne uwagi) |
| 6 | Ansible — utwardzenie VPS i wdrożenie stosu | `delivery:implementer` | `e7c4e76` feat(deploy): add Ansible playbook for VPS hardening and deployment | 1 |
| 7 | Potok CI/CD GitHub Actions i Dependabot | `delivery:implementer` | `4f16a2b` ci: add pipeline with scan gates, image build, stack smoke and GHCR publish | 1 |
| 8 | Push gałęzi, draft PR i dowód przebiegu CI | `delivery:implementer` | `fe314cb` docs: add CI run evidence for phase 3 | 0 (przyjęte drobne uwagi) |
| 9 | Dokumentacja Fazy 3 | `delivery:implementer` | bieżący commit dokumentacji: docs: add phase 3 ops report, DevSecOps report, prompt log and evidence | przegląd po zapisie dokumentacji |

Drobne uwagi z przeglądów zadań 5, 6 i 8, których nie poprawiono, trafiły do sekcji „Ryzyka rezydualne” w [`README.md`](README.md) (m.in. kolejność handlerów i brak prefiksu `-` przy `ExecStop` w roli `base`).

## 7. Odstępstwa wykonania od planu

Plan zawierał dosłowne treści plików; podczas wykonania zmieniono je tam, gdzie testy, skanery albo CI pokazały błąd. Dokumentacja opisuje stan faktyczny z repozytorium:

| Obszar | Plan | Stan faktyczny | Powód |
|---|---|---|---|
| Audit log ModSecurity | części `AFHZ` | `AHZ` (`deploy/proxy/Dockerfile`) | część F (nagłówki odpowiedzi) zapisywała `Set-Cookie` z tokenem sesji |
| HTTP/2 w proxy | nie wspomniano | `HTTP2=off` | podatności HTTP/2 w nginx 1.30.6; sześć CVE nginx w `.trivyignore` do 2026-12-19 (pięć niedotyczących konfiguracji i CVE-2026-118899, DoS przez TLS 1.3, przyjęte jako ryzyko po przebiegu CI), poprawka w 1.30.7-r0 nie jest jeszcze w tagu obrazu CRS |
| `Host` do API | `proxy_set_header Host $host` | stała `${SERVER_NAME}` | przekierowania Starlette odbijałyby `Host` od klienta (Semgrep, zadanie 3) |
| Adres w smoke | `https://127.0.0.1:<port>` | `https://patchpoint.localhost:<port>` | reguły CRS 920350 i 920180 razem blokują `POST` bez treści na numeryczny adres IP; sekrety poza argumentami procesów (jq przez stdin, ciasteczko w pliku 0600) |
| Tryb plików w obrazach | `COPY` bez trybu plików | symboliczne `COPY --chmod` (zadania 1–2), potem `chmod -R` w `RUN` dla katalogów z podkatalogami (zadanie 8); `COPY --chmod` zostaje dla plików bez podkatalogów | BuildKit w Dockerze 28 odbiera podkatalogom bit `x` (przebieg CI 44477002456; [`dowody/ci.md`](dowody/ci.md)) |
| Powłoka w CI | domyślna | `defaults.run.shell: bash` | `pipefail`, żeby `| tee` nie ukrywał błędu smoke |
| Ansible | role z planu | `python3-debian` w pakietach bazowych, drop-in `nftables.service`, `flush_handlers` roli `docker` przed rolą `patchpoint`, `patchpoint_seed_demo_data \| bool` | `deb822_repository` wymaga `python3-debian`; `nft flush ruleset` w domyślnym `ExecStop` usunąłby reguły Dockera |
| Trivy fs | bez wyjątków | `# trivy:ignore:DS-0031` przy osobnej instrukcji `ENV` | heurystyka bierze nazwy zmiennych za sekrety ([`dowody/triaz-skanow.md`](dowody/triaz-skanow.md)) |
