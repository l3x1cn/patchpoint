# Dziennik promptów AI — Faza 2 (SEC)

## 1. Narzędzia

Użyto Claude (Anthropic) uruchomionego w harnessie omp. Tryb planowania obejmował:

- analizę repozytorium i środowiska;
- weryfikację zachowań bibliotek i narzędzi: Starlette 1.10 (CORS i limit rozmiaru ciała żądania), curl i przeglądarki (ciasteczka `Secure` na `localhost`), `http.cookiejar` w kliencie testowym, `argon2-cffi` w PyPI oraz NIST SP 800-63B-4 (długość haseł);
- pytania doprecyzowujące do zespołu;
- ślepy audyt SAST w osobnym agencie, uruchomiony przed napisaniem planu;
- plan.

Realizację prowadziła wtyczka delivery:

- zadania 2–4 wykonał agent `python-developer:developer` (TDD, ruff, mypy);
- zadania 1 i 5–7 wykonał `delivery:implementer`;
- każdy wynik przed commitem przeglądał `delivery:task-reviewer`;
- po zadaniach przewidziano weryfikację z planu, QA i końcowy code review; ich wyniki powstają po tym dokumencie, w osobnych raportach (`docs/testing/reports/`, `docs/reviews/`).

## 2. Prompt nr 1 (zespół → AI)

Treść dosłownie, wraz z brakiem polskich znaków. Instrukcja kursu i scenariusz, na których opiera się Faza 2, były w prompcie nr 1 Fazy 1 ([`../faza-1-dev/prompty.md`](../faza-1-dev/prompty.md), sekcja 2); w Fazie 2 zespół użył dwóch krótkich poleceń.

Polecenie rozpoczynające fazę:

```text
doskonale, przejdz do fazy 2
```

Polecenie w trybie planowania:

```text
przygotuj plan implementacyjny fazy 2
```

## 3. Pytania doprecyzowujące AI i odpowiedzi zespołu

| Pytanie AI | Odpowiedź zespołu |
|---|---|
| Kiedy przeprowadzić ślepy audyt SAST z AI („Wirtualny Red Teamer”)? | Teraz, przed planem |
| Co naprawiamy w Fazie 2 poza W-01…W-18? | Bezpieczeństwo + jakość z review |

Przed pytaniami AI ustaliło z GitHuba, że PR #1 z Fazą 1 jest scalony (`origin/main` = `a59e790`), więc Faza 2 startuje od `main`, a kod Fazy 1 to drzewo commita `ab08633`.

## 4. Prompty nr 2–3 — dwie próby audytu Red Team

Prompty nr 2 i 3 to dosłowne polecenia wysłane do osobnego agenta `security-reviewer` (tylko odczyt, bez rejestru słabości i bez planu). Pełna treść obu, metadane i wynik każdej próby: [`audyt-red-team.md`](audyt-red-team.md), sekcja „Prompty”. Pierwszą próbę, z prośbą o krokowe scenariusze ataku, odrzucił filtr bezpieczeństwa modelu; druga, w ujęciu defensywnym (przegląd własnego kodu w celu naprawy), dała pełny audyt: [`audyt-red-team-wynik.md`](audyt-red-team-wynik.md).

## 5. Prompt nr 4 — plan wygenerowany przez AI

Czwartym „promptem” jest plan wygenerowany przez AI na podstawie poleceń z punktu 2, odpowiedzi z punktu 3 i wyniku audytu: siedem zadań z opisem zmian, testów i kryteriów „Gotowe, gdy”. Plan znajduje się w pliku [`docs/plans/2026-11-16-faza-2-sec.md`](../plans/2026-11-16-faza-2-sec.md). W Fazie 2 plan nie zawiera celowych słabości, a odstępstwo od opisanych w nim zachowań jest błędem.

## 6. Prompty nr 5–11 — zadania 1–7 przekazane agentom

Treść każdego zadania z planu (od „Task 1” do „Task 7”) została przekazana agentowi realizującemu w jednolitym szablonie delivery; w miejsce `<TASK_BLOCK>` wstawiany jest pełny blok zadania z planu:

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
| nr 5 | Zadanie 1 — audyt Red Team i threat model na kodzie Fazy 1 |
| nr 6 | Zadanie 2 — backend: konfiguracja, obsługa błędów, nagłówki i limity |
| nr 7 | Zadanie 3 — backend: hasła, sesje, logowanie i dane demo |
| nr 8 | Zadanie 4 — backend: zgłoszenia, SQL injection, IDOR, limity, paginacja i audyt zmian |
| nr 9 | Zadanie 5 — frontend: bezpieczne renderowanie, CSP, paginacja i obsługa sesji |
| nr 10 | Zadanie 6 — skrypty: PoC bezpieczeństwa, demo i konfiguracja QA |
| nr 11 | Zadanie 7 — dokumentacja Fazy 2, raport Sekcji Sec, dziennik promptów i dowody |

## 7. Zadanie → agent → commit

Commity zadań 1–6 pochodzą z polecenia `git log --format='%h %s%n%b' --grep='Delivery-Task:'`. Rundy poprawek to kolejne przejścia agenta po uwagach `delivery:task-reviewer` przed commitem.

| Zadanie | Tytuł | Agent | Commit | Rundy poprawek |
|---|---|---|---|---|
| 1 | Audyt Red Team i threat model na kodzie Fazy 1 | `delivery:implementer` | `463f712` docs: add red team audit and threat model for phase 2 | 0 |
| 2 | Backend — bezpieczna konfiguracja, obsługa błędów, nagłówki i limity | `python-developer:developer` | `6f742bc` fix(backend): harden error handling, CORS, API docs exposure and response headers | 0 |
| 3 | Backend — hasła, sesje, logowanie i dane demo | `python-developer:developer` | `b295c85` fix(backend): secure passwords, sessions, login and demo accounts | 1 (`transaction()` musi cofać zmiany także po `BaseException`) |
| 4 | Backend — zgłoszenia: SQL injection, IDOR, limity, paginacja i audyt zmian | `python-developer:developer` | `dfc2547` fix(backend): parameterize ticket queries and enforce ticket ownership | 0 |
| 5 | Frontend — bezpieczne renderowanie, CSP, paginacja i obsługa sesji | `delivery:implementer` | `c092230` fix(frontend): render API data as text and add CSP, pagination and session handling | 1 (wartość `null` widoczna w szczegółach zgłoszenia pracownika) |
| 6 | Skrypty — PoC bezpieczeństwa, demo i konfiguracja QA | `delivery:implementer` | `4bfaeb1` chore(scripts): add security regression check and update demo and QA setup | 1 (fałszywie dodatni wynik blokady W-12 przy powtórnych uruchomieniach PoC) |
| 7 | Dokumentacja Fazy 2, raport Sekcji Sec, dziennik promptów i dowody | `delivery:implementer` | bieżący commit dokumentacji: docs: add phase 2 security report, prompt log and evidence | przegląd po zapisie dokumentacji |

Uwagi z przeglądów zadań, których nie poprawiono w Fazie 2, trafiły do sekcji „Ryzyka rezydualne i przekazanie do Fazy 3” w [`README.md`](README.md): hashowanie Argon2 działa synchronicznie w asynchronicznym handlerze logowania, a testy nie sprawdzają zdarzeń `login_blocked`, `login_failed` z powodem `unknown_user` ani `logout`.
