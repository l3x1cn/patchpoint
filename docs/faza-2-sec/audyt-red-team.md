# Audyt SAST z AI — „Wirtualny Red Teamer” (Faza 2)

Dokument realizuje pierwszy punkt Fazy 2: AI w roli „Wirtualnego Red Teamera” wykonało statyczną analizę kodu (SAST) aplikacji PatchPoint według listy OWASP Top 10:2025. Wynik audytu zapisano dosłownie w [`audyt-red-team-wynik.md`](audyt-red-team-wynik.md). Weryfikacja znalezisk (threat modeling) znajduje się w [`threat-model.md`](threat-model.md).

## Metadane

| Parametr | Wartość |
|---|---|
| Data | 2026-11-16 |
| Narzędzie | Claude (Anthropic) w harnessie omp, agent `security-reviewer` (tylko odczyt), uruchomiony z sesji planowania Fazy 2 |
| Model | `anthropic/claude-opus-5-5` |
| Zakres | `backend/app/**` i `frontend/**` (15 plików), stan kodu `ab08633` |
| Wejście agenta | wyłącznie prompt, bez rejestru słabości, planu i historii rozmowy |
| Próby | 2. Pierwszą odrzucił filtr bezpieczeństwa modelu po 27,9 s; druga trwała 4 min 58 s |
| Wynik | 16 luk RT-01…RT-16 (3 krytyczne, 6 wysokich, 4 średnie, 3 niskie) |

## Prompty

Oba prompty wysłano 2026-11-16 z sesji planowania (Claude w harnessie omp) do osobnego agenta `security-reviewer` (tryb tylko do odczytu, model `anthropic/claude-opus-5-5`) przez narzędzie `task`. Agent otrzymał wyłącznie pole `context` i treść zadania poniżej — bez rejestru słabości, planu ani historii rozmowy.

### Próba 1 — odrzucona

Wynik: po 27,9 s agent zakończył się błędem. Komunikat w całości:

```text
[anthropic/claude-opus-5-5] Refusal (cyber): Cyber safeguards flagged this message. If this is legitimate security work, you can apply for the Cyber Verification Program: https://support.claude.com/en/articles/14604842-cyber-verification-program.
```

Pole `context`:

```text
# Goal
Statyczny audyt bezpieczeństwa (SAST) w roli Red Teamera. Wynikiem jest raport Markdown zwrócony jako odpowiedź końcowa. Pracujesz wyłącznie w trybie odczytu.
```

Treść zadania:

```text
Wciel się w rolę „Wirtualnego Red Teamera”: doświadczonego pentestera aplikacji webowych, który przed testem penetracyjnym wykonuje statyczną analizę kodu źródłowego (SAST, white-box).

Cel: PatchPoint, system wsparcia technicznego do zgłaszania awarii sprzętowych przez pracowników do działu Helpdesk. Pracownik (rola `employee`) zgłasza awarie i komentuje swoje zgłoszenia; agent Helpdesku (rola `agent`) widzi wszystkie zgłoszenia, zmienia ich status i przypisanie. Backend: Python, FastAPI, SQLite (moduł sqlite3). Frontend: statyczny HTML/JS serwowany z osobnego originu (http://localhost:5500), który wywołuje API (http://localhost:8000) przez fetch z cookie sesyjnym.

Kluczowe wektory ataku dla tego systemu: Information Disclosure (nadmiernie gadatliwe błędy ujawniające architekturę bazy danych) oraz Broken Authentication (np. słabe zarządzanie sesją). Istotna jest też bezpieczna konfiguracja nagłówków CORS przy rozdzieleniu frontendu i backendu.

Zakres: wyłącznie pliki w katalogach `backend/app/` i `frontend/` repozytorium `/home/lex/Projects/patchpoint` (stan kodu: commit `ab08633`). Nie otwieraj żadnych innych plików ani katalogów — w szczególności `docs/`, `README.md`, `backend/tests/`, `scripts/`, `.av/`, `Makefile` — i nie przeglądaj historii git. Nie uruchamiaj aplikacji ani narzędzi skanujących: to analiza statyczna kodu.

Zadanie:
1. Przeanalizuj cały kod w zakresie i wskaż podatności bezpieczeństwa, klasyfikując je według listy OWASP Top 10:2025 (A01–A10).
2. Dla każdej podatności podaj: identyfikator `RT-NN`, tytuł, kategorię OWASP Top 10:2025 (główną i ewentualnie pomocnicze), CWE, lokalizację (plik, linia, funkcja), opis, scenariusz ataku krok po kroku z przykładowym żądaniem HTTP lub payloadem, wpływ, ważność (krytyczna / wysoka / średnia / niska) z uzasadnieniem, pewność (wysoka / średnia / niska) i rekomendację naprawy.
3. Opisz łańcuchy ataku łączące kilka podatności.
4. Zgłaszaj tylko to, co wynika z kodu. Jeśli czegoś nie da się potwierdzić statycznie, ustaw pewność „niska” i napisz, czego brakuje.

Format odpowiedzi (Markdown, po polsku; identyfikatory, ścieżki i kod w oryginale):
1. Tabela zbiorcza: ID | Tytuł | OWASP Top 10:2025 | CWE | Lokalizacja | Ważność | Pewność.
2. Sekcja szczegółowa dla każdego `RT-NN`.
3. Sekcja „Łańcuchy ataku”.
4. Sekcja „Przeczytane pliki”: lista wszystkich plików, które otworzyłeś.

Odpowiedź końcowa to wyłącznie ten raport Markdown.
```

### Próba 2 — wykonana (wynik w `audyt-red-team.md`)

Zmiany względem próby 1: ujęcie defensywne (przegląd własnego kodu w celu naprawy), rezygnacja z prośby o kroki ataku z payloadami na rzecz koncepcyjnego opisu nadużycia (1–3 zdania), „Powiązania między lukami” zamiast „Łańcuchów ataku”. Zakres, opis systemu, kategorie OWASP i format wyniku bez zmian. Czas pracy agenta: 4 min 58 s.

Pole `context`:

```text
# Goal
Defensywny przegląd bezpieczeństwa kodu (SAST) aplikacji kursowej zespołu. Wynikiem jest raport Markdown zwrócony jako odpowiedź końcowa. Pracujesz wyłącznie w trybie odczytu.
```

Treść zadania:

```text
Rola: „Wirtualny Red Teamer” w projekcie kursu „AI-Driven DevSecOps” — audytor bezpieczeństwa aplikacji, który ocenia kod z perspektywy możliwych nadużyć, żeby zespół mógł go naprawić. To defensywny przegląd własnego kodu zespołu (aplikacja kursowa uruchamiana tylko lokalnie); gotowe exploity nie są potrzebne.

Aplikacja: PatchPoint, system wsparcia technicznego do zgłaszania awarii sprzętowych przez pracowników do działu Helpdesk. Pracownik (rola `employee`) zgłasza awarie i komentuje swoje zgłoszenia; agent Helpdesku (rola `agent`) widzi wszystkie zgłoszenia, zmienia ich status i przypisanie. Backend: Python, FastAPI, SQLite (moduł sqlite3). Frontend: statyczny HTML/JS serwowany z osobnego originu (http://localhost:5500), który wywołuje API (http://localhost:8000) przez fetch z cookie sesyjnym.

Obszary ryzyka szczególnie istotne w tym scenariuszu: Information Disclosure (nadmiernie gadatliwe błędy ujawniające architekturę bazy danych), Broken Authentication (np. słabe zarządzanie sesją) oraz bezpieczna konfiguracja nagłówków CORS przy rozdzieleniu frontendu i backendu.

Zakres: wyłącznie pliki w katalogach `backend/app/` i `frontend/` repozytorium `/home/lex/Projects/patchpoint` (stan kodu: commit `ab08633`). Nie otwieraj żadnych innych plików ani katalogów — w szczególności `docs/`, `README.md`, `backend/tests/`, `scripts/`, `.av/`, `Makefile` — i nie przeglądaj historii git. Nie uruchamiaj aplikacji ani narzędzi: to statyczna analiza kodu.

Zadanie: przeprowadź statyczną analizę kodu (SAST) i wskaż luki bezpieczeństwa, klasyfikując je według listy OWASP Top 10:2025 (A01–A10). Dla każdej luki podaj:
- identyfikator `RT-NN` i tytuł;
- kategorię OWASP Top 10:2025 (główną i ewentualnie pomocnicze) oraz CWE;
- lokalizację (plik, linia, funkcja);
- opis błędu w kodzie;
- jak błąd mógłby zostać nadużyty — opis koncepcyjny w 1–3 zdaniach;
- wpływ;
- ważność (krytyczna / wysoka / średnia / niska) z uzasadnieniem oraz pewność (wysoka / średnia / niska);
- rekomendację naprawy (mechanizm i miejsce w kodzie).

Wskaż też, które luki wzmacniają się nawzajem. Zgłaszaj tylko to, co wynika z kodu; czego nie da się potwierdzić statycznie, oznacz pewnością „niska” z uzasadnieniem.

Format odpowiedzi (Markdown, po polsku; identyfikatory, ścieżki i kod w oryginale):
1. Tabela zbiorcza: ID | Tytuł | OWASP Top 10:2025 | CWE | Lokalizacja | Ważność | Pewność.
2. Sekcja szczegółowa dla każdego `RT-NN`.
3. Sekcja „Powiązania między lukami”.
4. Sekcja „Przeczytane pliki”: lista wszystkich plików, które otworzyłeś.

Odpowiedź końcowa to wyłącznie ten raport Markdown.
```

### Weryfikacja „ślepoty” audytu (z transkryptu agenta próby 2)

- `glob`: `backend/app/**`, `frontend/**`;
- `read` (16 wywołań, 15 plików): `backend/app/main.py`, `database.py`, `dependencies.py`, `security.py`, `config.py`, `schemas.py`, `routers/auth.py`, `routers/tickets.py`, `routers/health.py`, `schema.sql`, `__init__.py`, `routers/__init__.py`, `frontend/app.js` (dwa odczyty), `frontend/index.html`, `frontend/styles.css`;
- `grep` (4 wywołania): ścieżki `backend/app` (2×) i `frontend` (2×);
- brak odczytów `docs/`, `README.md`, testów, skryptów, `.av/` i historii git; brak uruchomień poleceń.

## Wniosek z odrzuconej próby

Filtr bezpieczeństwa modelu odrzucił prośbę o krokowe scenariusze ataku z payloadami. Ujęcie defensywne (przegląd własnego kodu w celu naprawy, koncepcyjny opis nadużycia) dało pełny audyt. Rolę „Red Teamera” pełni więc AI jako recenzent SAST, a odtworzenie ataków zapewnia własny skrypt PoC zespołu (`scripts/security_check.sh`, dodawany w Fazie 2).
