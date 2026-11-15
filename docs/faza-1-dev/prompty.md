# Dziennik promptów AI — Faza 1 (DEV)

## 1. Narzędzia

Użyto Claude (Anthropic) uruchomionego w harnessie omp. Tryb planowania obejmował analizę repozytorium i środowiska, weryfikację wersji pakietów w PyPI i kodu Starlette (CORS), pytania doprecyzowujące, plan i jego przegląd przez model doradczy. Realizację prowadziła wtyczka delivery:

- zadania 1–2 wykonał agent `python-developer:developer` (TDD, ruff, mypy);
- zadania 3–5 wykonał `delivery:implementer`;
- każdy wynik przed commitem przeglądał `delivery:task-reviewer` (do 3 rund poprawek);
- po zadaniach przewidziano weryfikację z planu, QA i końcowy code review; ich wyniki powstają po tym dokumencie, w osobnych raportach.

## 2. Prompt nr 1 (zespół → AI, tryb planowania)

Treść dosłownie, wraz z literówkami i brakiem polskich znaków:

```text
do przygotowania jest projekt z takimi zalozeniami: Instrukcja Realizacji Projektu: AI-Driven DevSecOps
Zadaniem Waszego zespołu jest wygenerowanie, zabezpieczenie i przygotowanie do
wdrożenia chmurowego przydzielonej mikrousługi webowej. W ramach projektu
pełnicie naprzemiennie role Programistów (Dev), Inżynierów Bezpieczeństwa (Sec)
oraz Inżynierów Chmurowych (Ops), wykorzystując modele LLM jako asystentów na
każdym etapie prac.
Faza 1: DEV (Generowanie Kodu)
● Wykorzystajcie wybrane narzędzie AI (np. ChatGPT, Gemini, Claude), aby
wygenerować działający kod backendu (np. w Python/FastAPI,
Node.js/Express lub PHP) dla Waszego scenariusza.
● Zadbajcie o to, aby aplikacja realizowała podstawową logikę biznesową i
posiadała komunikację z bazą danych (np. SQLite dla uproszczenia testów).
● Celowo poproście AI o szybki kod (Draft/MVP), aby pozostawić przestrzeń na
luki bezpieczeństwa. Udowodnijcie, że kod się uruchamia i realizuje swoje
funkcje.
Faza 2: SEC (Audyt i Remediacja z AI)
● Zmieńcie rolę i stwórzcie z AI "Wirtualnego Red Teamera". Przeprowadźcie
statyczną analizę wygenerowanego kodu (SAST), prosząc o wskazanie luk z
listy OWASP Top 10.
● Zweryfikujcie poprawność wykrytych podatności (Threat Modeling) dla
Waszego konkretnego wektora ataku opisanego w scenariuszu.
● Wykorzystajcie AI do naprawienia kodu (np. wdrożenie parametryzacji
zapytań SQL, sanityzacji wejścia, ukrycia ścieżek). Sprawdźcie, czy połatana
aplikacja nadal poprawnie funkcjonuje.
Faza 3: OPS (Infrastruktura i Automatyzacja)
● Aplikacja musi działać w chmurze. Zaprojektujcie bezpieczny plik
Dockerfile (wymagane m.in. zasada rootless, multi-stage build, okrojony
obraz bazowy).

● Wygenerujcie z AI definicję potoku wdrożeniowego CI/CD (np. plik YAML dla
GitHub Actions lub GitLab CI), który przed zbudowaniem obrazu
automatycznie uruchomi narzędzia skanujące (np. Semgrep, Trivy).
● Zaprojektujcie logiczną architekturę sieciową dla Waszego rozwiązania.
Efekt Końcowy (Wymagane Dokumenty Zaliczeniowe)
Każdy zespół musi oddać repozytorium kodu (lub paczkę plików) zawierające
następujące elementy:
1. Działający, bezpieczny kod aplikacji: Finalna wersja kodu połatana w
Fazie 2.
2. Bezpieczny Dockerfile: Zgodny z chmurowymi praktykami least privilege.
3. Pipeline CI/CD (.yaml): Kod potoku automatyzującego skanowanie i
budowanie.
4. Raport Architektoniczny DevSecOps (Dokumentacja w formacie
Markdown lub PDF), zawierający:
○ Sekcję Sec: Zestawienie luk wykrytych w Fazie 1, opis wektorów ataku
oraz wyjaśnienie, jakich mechanizmów użyto do ich naprawy.
○ Sekcję Ops: Opis docelowego środowiska chmurowego (np.
zarysowanie podsieci prywatnych/publicznych, zastosowanie WAF,
sposób zarządzania zmiennymi środowiskowymi i sekretami w
chmurze). \n\n scenariusz wyglada tak: Scenariusz 5: Menadżer Zadań IT (IT Ticketing System)
● Funkcja: System wsparcia technicznego do zgłaszania awarii
sprzętowych przez pracowników do działu Helpdesk.
● Kluczowe wektory ataku (Focus SEC): Information
Disclosure (nadmiernie gadatliwe błędy ujawniające architekturę
bazy danych) oraz Broken Authentication (np. słabe zarządzanie
sesją). Bezpieczna konfiguracja nagłówków CORS przy rozdzieleniu
frontend/backend.  \n\n przygotowane zostalo repozytorium git. przygotuj plan implementacyjny fazy 1. dokumentacja rowniez jest wazna.
```

## 3. Pytania doprecyzowujące AI i odpowiedzi zespołu

| Pytanie AI | Odpowiedź zespołu |
|---|---|
| W jakim stosie generujemy backend MVP? | Python + FastAPI + SQLite |
| Jak zarządzać zależnościami (uv nie był zainstalowany)? | uv (doinstalować) |
| Czy w Fazie 1 powstaje frontend? | minimalny frontend HTML/JS |
| Język dokumentacji? | polski (kod po angielsku) |
| Czy dokumentacja ma zawierać rejestr celowo pozostawionych słabości? | tak, pełny rejestr w docs |

## 4. Prompt nr 2 — plan wygenerowany przez AI

Drugim „promptem” jest plan wygenerowany przez AI na podstawie promptu nr 1 i odpowiedzi z punktu 3: specyfikacja pięciu zadań z wymaganiami oznaczonymi `[W-xx]`. Plan znajduje się w pliku [`docs/plans/2026-11-15-faza-1-mvp.md`](../plans/2026-11-15-faza-1-mvp.md).

Instrukcja „Draft/MVP” z promptu nr 1 przełożyła się w planie na dwa elementy: wymagania W-xx, czyli celowo uproszczone rozwiązania, które mają stanowić materiał dla audytu w Fazie 2 (zestawienie w [`rejestr-slabosci.md`](rejestr-slabosci.md)), oraz zakaz umieszczania w kodzie komentarzy, docstringów i nazw zdradzających słabości, tak aby audyt AI znalazł je samodzielnie.

## 5. Prompty nr 3–7 — zadania 1–5 przekazane agentom

Treść każdego zadania z planu (od „Task 1” do „Task 5”) została przekazana agentowi realizującemu w jednolitym szablonie delivery; w miejsce `<TASK_BLOCK>` wstawiany jest pełny blok zadania z planu:

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
| nr 3 | Zadanie 1 — szkielet API, SQLite i uwierzytelnianie sesyjne |
| nr 4 | Zadanie 2 — zgłoszenia, przepływ statusów, komentarze i dane demo |
| nr 5 | Zadanie 3 — statyczny klient HTML/JS na osobnym originie |
| nr 6 | Zadanie 4 — skrypt demonstracyjny end-to-end |
| nr 7 | Zadanie 5 — dokumentacja, rejestr słabości i dowody działania |

## 6. Zadanie → agent → commit

Commity zadań 1–4 pochodzą z polecenia `git log --format='%h %s%n%b' --grep='Delivery-Task:'`.

| Zadanie | Tytuł | Agent | Commit |
|---|---|---|---|
| 1 | Backend — szkielet API, SQLite i uwierzytelnianie sesyjne | `python-developer:developer` | `bbeb8cd` feat(backend): add FastAPI MVP skeleton with SQLite and session auth |
| 2 | Backend — zgłoszenia, przepływ statusów, komentarze i dane demo | `python-developer:developer` | `5e89a0d` feat(backend): add ticket workflow, comments and demo data |
| 3 | Frontend — statyczny klient HTML/JS na osobnym originie | `delivery:implementer` | `9013051` feat(frontend): add static helpdesk client on a separate origin |
| 4 | Skrypt demonstracyjny end-to-end | `delivery:implementer` | `8a968e9` chore(scripts): add end-to-end API demo script |
| 5 | Dokumentacja Fazy 1, rejestr słabości i dowody działania | `delivery:implementer` | bieżący commit dokumentacji: docs: add phase 1 report, prompt log, weakness register and run evidence |
