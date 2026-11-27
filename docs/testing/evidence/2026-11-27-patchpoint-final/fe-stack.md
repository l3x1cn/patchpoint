# FE-01 – FE-06: browser scenarios through the `patchpoint-final` stack

Plan: `docs/testing/plans/2026-11-27-patchpoint-final-test-plan.md` (FE Test Scenarios). Date: 2026-11-27.
Branch `delivery/patchpoint-final-testing`, stack `patchpoint-final` in local mode, `H` = `http://patchpoint.localhost:28080`, `$SFX` = `e39a69`.
Users: `qa.final.$SFX.owner` (registered in FE-01) and the seeded agent `helpdesk`. Passwords were typed from files under `$RUN`; this file contains no password, no cookie value and no `Set-Cookie` header.

## How the browser was driven

The OMP `eval`/`browser` global is not available in this session (the agent has no `eval` tool and `xd://eval` does not exist), so the scenarios were NOT run through `browser.open`. They were run in the same engine, Chromium `157.0.8103.79` (`/usr/bin/chromium --headless`), through one tab driven over the Chrome DevTools Protocol (pipe) by a throwaway dependency-free Node script kept in `$RUN` (deleted at the end of the task). Mapping to the plan's vocabulary:

| Plan | Driver |
|---|---|
| `browser.open` / `tab.goto` | `Page.navigate` / `Page.reload` (op `goto`, `reload`) |
| fill a field by its visible label | focus by a real mouse click, select all, `Input.insertText` (op `fill`; the `Hasło` fields are filled from a file, the value is never printed) |
| choose an option | set `<select>` value by the option's visible text and dispatch `input` and `change` (op `select`, `selectId`) |
| click a button / a list row | real mouse press and release at the element centre (op `click`, `clickRow`) |
| `tab.evaluate` | `Runtime.evaluate` with `awaitPromise` (op `eval`) |

Each record is `[label]`, the JSON action sent to the driver (`$RUN` = private temp directory) and the `state` returned. After every click the driver waits (`wait`, ms) and returns a snapshot of the page: `message` = text of `#message` (+ its CSS class), `authViewVisible`/`appViewVisible`, `userBar` = text of the user bar, `rows` = the ticket list rows, `detailHeading` = the `<h2>` of the ticket detail, `statusSelect`/`assignButton` = whether `#status-select` and `#assign-button` exist. Before every sign-up and sign-in submit (except FE-06) the shell slept 7 s (pacing, not recorded as an action). No screenshots were taken.

Note on the environment: the session cookie is `Secure` (see `ops-stack.txt`, OPS-04). Chromium accepts it on `http://*.localhost`, so the browser scenarios were not affected.

## FE-01: Sign-up and sign-in through the proxy

```
[FE-01 start]
action: {"op":"goto","url":"http://patchpoint.localhost:28080/"}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"","messageClass":"","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-01 step 1: fill Login]
action: {"op":"fill","form":"#register-form","label":"Login","text":"qa.final.e39a69.owner"}
state:  {"ok":true,"result":{"filled":"#register-form \"Login\"","length":21,"fromFile":false}}

[FE-01 step 1: fill Imię i nazwisko]
action: {"op":"fill","form":"#register-form","label":"Imię i nazwisko","text":"QA Final Owner"}
state:  {"ok":true,"result":{"filled":"#register-form \"Imię i nazwisko\"","length":14,"fromFile":false}}

[FE-01 step 1: fill Dział]
action: {"op":"fill","form":"#register-form","label":"Dział","text":"QA"}
state:  {"ok":true,"result":{"filled":"#register-form \"Dział\"","length":2,"fromFile":false}}

[FE-01 step 1: fill Hasło (from file)]
action: {"op":"fill","form":"#register-form","label":"Hasło","file":"$RUN/pw.qa.final.e39a69.owner"}
state:  {"ok":true,"result":{"filled":"#register-form \"Hasło\"","length":27,"fromFile":true}}

[FE-01 step 1: form values before submit (passwords omitted)]
action: {"op":"form","form":"#register-form"}
state:  {"ok":true,"result":{"form":["username=qa.final.e39a69.owner","full_name=QA Final Owner","department=QA"]}}

[FE-01 step 1: click Zarejestruj konto]
action: {"op":"click","scope":"#register-form","text":"Zarejestruj konto","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Konto utworzone — możesz się zalogować","messageClass":"success","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-01 edge a: fill Login]
action: {"op":"fill","form":"#register-form","label":"Login","text":"qa.final.e39a69.owner"}
state:  {"ok":true,"result":{"filled":"#register-form \"Login\"","length":21,"fromFile":false}}

[FE-01 edge a: fill Imię i nazwisko]
action: {"op":"fill","form":"#register-form","label":"Imię i nazwisko","text":"QA Final Owner"}
state:  {"ok":true,"result":{"filled":"#register-form \"Imię i nazwisko\"","length":14,"fromFile":false}}

[FE-01 edge a: fill Dział]
action: {"op":"fill","form":"#register-form","label":"Dział","text":"QA"}
state:  {"ok":true,"result":{"filled":"#register-form \"Dział\"","length":2,"fromFile":false}}

[FE-01 edge a: fill Hasło (from file)]
action: {"op":"fill","form":"#register-form","label":"Hasło","file":"$RUN/pw.qa.final.e39a69.owner"}
state:  {"ok":true,"result":{"filled":"#register-form \"Hasło\"","length":27,"fromFile":true}}

[FE-01 edge a: click Zarejestruj konto (same registration again)]
action: {"op":"click","scope":"#register-form","text":"Zarejestruj konto","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Username is already taken","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-01 edge b: fill Login]
action: {"op":"fill","form":"#register-form","label":"Login","text":"qa.final.e39a69.owner2"}
state:  {"ok":true,"result":{"filled":"#register-form \"Login\"","length":22,"fromFile":false}}

[FE-01 edge b: fill Imię i nazwisko]
action: {"op":"fill","form":"#register-form","label":"Imię i nazwisko","text":"QA Final Owner Two"}
state:  {"ok":true,"result":{"filled":"#register-form \"Imię i nazwisko\"","length":18,"fromFile":false}}

[FE-01 edge b: fill Dział]
action: {"op":"fill","form":"#register-form","label":"Dział","text":"QA"}
state:  {"ok":true,"result":{"filled":"#register-form \"Dział\"","length":2,"fromFile":false}}

[FE-01 edge b: fill Hasło (from file; password = login + "-Secret-12345")]
action: {"op":"fill","form":"#register-form","label":"Hasło","file":"$RUN/pw.owner2"}
state:  {"ok":true,"result":{"filled":"#register-form \"Hasło\"","length":35,"fromFile":true}}

[FE-01 edge b: click Zarejestruj konto]
action: {"op":"click","scope":"#register-form","text":"Zarejestruj konto","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Value error, Password must not contain the username","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-01 step 3: fill Login (Logowanie)]
action: {"op":"fill","form":"#login-form","label":"Login","text":"qa.final.e39a69.owner"}
state:  {"ok":true,"result":{"filled":"#login-form \"Login\"","length":21,"fromFile":false}}

[FE-01 step 3: fill Hasło (Logowanie, from file)]
action: {"op":"fill","form":"#login-form","label":"Hasło","file":"$RUN/pw.qa.final.e39a69.owner"}
state:  {"ok":true,"result":{"filled":"#login-form \"Hasło\"","length":27,"fromFile":true}}

[FE-01 step 3: click Zaloguj]
action: {"op":"click","scope":"#login-form","text":"Zaloguj","wait":1500}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"","messageClass":"","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: QA Final Owner (pracownik)","rows":["Brak zgłoszeń."],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-01 step 3: document.cookie contains session=]
action: {"op":"eval","expr":"({cookie: document.cookie, hasSession: document.cookie.includes(\"session=\")})"}
state:  {"ok":true,"result":{"value":{"cookie":"","hasSession":false}}}

```

Result FE-01: **Pass**.
- Step 1: `#message` = „Konto utworzone — możesz się zalogować” (class `success`).
- Edge a): „Username is already taken”.
- Edge b): „Value error, Password must not contain the username” (contains the expected text).
- Step 3: app view shown, user bar „Zalogowano: QA Final Owner (pracownik)”, `document.cookie` is `""` (`hasSession` false).

## FE-02: Employee ticket through the UI

```
[FE-02 step 1: fill Tytuł]
action: {"op":"fill","form":"#ticket-form","label":"Tytuł","text":"Drukarka nie drukuje e39a69"}
state:  {"ok":true,"result":{"filled":"#ticket-form \"Tytuł\"","length":27,"fromFile":false}}

[FE-02 step 1: select Kategoria]
action: {"op":"select","form":"#ticket-form","label":"Kategoria","option":"Drukarka"}
state:  {"ok":true,"result":{"selected":"printer=Drukarka"}}

[FE-02 step 1: select Priorytet]
action: {"op":"select","form":"#ticket-form","label":"Priorytet","option":"Wysoki"}
state:  {"ok":true,"result":{"selected":"high=Wysoki"}}

[FE-02 step 1: fill Opis]
action: {"op":"fill","form":"#ticket-form","label":"Opis","text":"Brak wydruku z kolejki."}
state:  {"ok":true,"result":{"filled":"#ticket-form \"Opis\"","length":23,"fromFile":false}}

[FE-02 step 1: click Wyślij zgłoszenie]
action: {"op":"click","scope":"#ticket-form","text":"Wyślij zgłoszenie","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Zgłoszenie wysłane","messageClass":"success","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: QA Final Owner (pracownik)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Otwarte | QA Final Owner | — | 27.11.2026, 23:52:52"],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-02 step 2: click the row]
action: {"op":"clickRow","title":"Drukarka nie drukuje e39a69","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Zgłoszenie wysłane","messageClass":"success","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: QA Final Owner (pracownik)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Otwarte | QA Final Owner | — | 27.11.2026, 23:52:52"],"detailHeading":"#4 Drukarka nie drukuje e39a69","statusSelect":false,"assignButton":false}}

[FE-02 step 3: fill Nowy komentarz]
action: {"op":"fill","form":"#comment-form","label":"Nowy komentarz","text":"Sprawdziłem kabel."}
state:  {"ok":true,"result":{"filled":"#comment-form \"Nowy komentarz\"","length":18,"fromFile":false}}

[FE-02 step 3: click Dodaj komentarz]
action: {"op":"click","scope":"#comment-form","text":"Dodaj komentarz","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Komentarz dodany","messageClass":"success","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: QA Final Owner (pracownik)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Otwarte | QA Final Owner | — | 27.11.2026, 23:52:52"],"detailHeading":"#4 Drukarka nie drukuje e39a69","statusSelect":false,"assignButton":false}}

[FE-02 step 3: comment list text]
action: {"op":"eval","expr":"[...document.querySelectorAll(\"#ticket-detail ul.comments li\")].map((li) => li.textContent.replace(/\\s+/g, \" \").trim())"}
state:  {"ok":true,"result":{"value":["QA Final Owner 27.11.2026, 23:52:55Sprawdziłem kabel."]}}

[FE-02 edge a: fill Tytuł]
action: {"op":"fill","form":"#ticket-form","label":"Tytuł","text":"<script>alert(1)</script>"}
state:  {"ok":true,"result":{"filled":"#ticket-form \"Tytuł\"","length":25,"fromFile":false}}

[FE-02 edge a: select Kategoria]
action: {"op":"select","form":"#ticket-form","label":"Kategoria","option":"Drukarka"}
state:  {"ok":true,"result":{"selected":"printer=Drukarka"}}

[FE-02 edge a: select Priorytet]
action: {"op":"select","form":"#ticket-form","label":"Priorytet","option":"Wysoki"}
state:  {"ok":true,"result":{"selected":"high=Wysoki"}}

[FE-02 edge a: fill Opis]
action: {"op":"fill","form":"#ticket-form","label":"Opis","text":"Brak wydruku z kolejki."}
state:  {"ok":true,"result":{"filled":"#ticket-form \"Opis\"","length":23,"fromFile":false}}

[FE-02 edge a: click Wyślij zgłoszenie]
action: {"op":"click","scope":"#ticket-form","text":"Wyślij zgłoszenie","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Request blocked by the proxy","messageClass":"error","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: QA Final Owner (pracownik)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Otwarte | QA Final Owner | — | 27.11.2026, 23:52:52"],"detailHeading":"#4 Drukarka nie drukuje e39a69","statusSelect":false,"assignButton":false}}

[FE-02 edge a: form values kept after the blocked submit]
action: {"op":"form","form":"#ticket-form"}
state:  {"ok":true,"result":{"form":["title=<script>alert(1)</script>","category=printer","priority=high","asset_tag=","location=","description=Brak wydruku z kolejki."]}}

[FE-02 edge a: dialogs and page exceptions so far]
action: {"op":"dialogs"}
state:  {"ok":true,"result":{"dialogs":[],"consoleErrors":[]}}

[FE-02 edge b: fill Szukaj]
action: {"op":"fill","form":"#filter-form","label":"Szukaj","text":"e39a69"}
state:  {"ok":true,"result":{"filled":"#filter-form \"Szukaj\"","length":6,"fromFile":false}}

[FE-02 edge b: click Filtruj]
action: {"op":"click","scope":"#filter-form","text":"Filtruj","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Request blocked by the proxy","messageClass":"error","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: QA Final Owner (pracownik)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Otwarte | QA Final Owner | — | 27.11.2026, 23:52:52"],"detailHeading":"#4 Drukarka nie drukuje e39a69","statusSelect":false,"assignButton":false}}

[FE-02 edge b: resource timing of the filter request (path, HTTP status)]
action: {"op":"eval","expr":"performance.getEntriesByType(\"resource\").filter((e) => e.name.includes(\"search=\")).map((e) => e.name.replace(location.origin, \"\") + \" -> \" + e.responseStatus)"}
state:  {"ok":true,"result":{"value":["/api/tickets?search=e39a69&limit=50&offset=0 -> 200"]}}

[FE-02 edge b: control, fill Szukaj with a string that matches nothing]
action: {"op":"fill","form":"#filter-form","label":"Szukaj","text":"zzz-no-match"}
state:  {"ok":true,"result":{"filled":"#filter-form \"Szukaj\"","length":12,"fromFile":false}}

[FE-02 edge b: control, click Filtruj]
action: {"op":"click","scope":"#filter-form","text":"Filtruj","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Request blocked by the proxy","messageClass":"error","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: QA Final Owner (pracownik)","rows":["Brak zgłoszeń."],"detailHeading":"#4 Drukarka nie drukuje e39a69","statusSelect":false,"assignButton":false}}

[FE-02 edge b: restore Szukaj]
action: {"op":"fill","form":"#filter-form","label":"Szukaj","text":"e39a69"}
state:  {"ok":true,"result":{"filled":"#filter-form \"Szukaj\"","length":6,"fromFile":false}}

[FE-02 edge b: click Filtruj again]
action: {"op":"click","scope":"#filter-form","text":"Filtruj","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Request blocked by the proxy","messageClass":"error","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: QA Final Owner (pracownik)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Otwarte | QA Final Owner | — | 27.11.2026, 23:52:52"],"detailHeading":"#4 Drukarka nie drukuje e39a69","statusSelect":false,"assignButton":false}}

[FE-02 edge b: resource timing of all filter requests]
action: {"op":"eval","expr":"performance.getEntriesByType(\"resource\").filter((e) => e.name.includes(\"search=\")).map((e) => e.name.replace(location.origin, \"\") + \" -> \" + e.responseStatus)"}
state:  {"ok":true,"result":{"value":["/api/tickets?search=e39a69&limit=50&offset=0 -> 200","/api/tickets?search=zzz-no-match&limit=50&offset=0 -> 200","/api/tickets?search=e39a69&limit=50&offset=0 -> 200"]}}

```

Result FE-02: **Pass**.
- Step 1: „Zgłoszenie wysłane”, one row `4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Otwarte | …`.
- Step 2: detail heading `#4 Drukarka nie drukuje e39a69`, `statusSelect` false, `assignButton` false.
- Step 3: „Komentarz dodany”, the comment list holds `Sprawdziłem kabel.`.
- Edge a): „Request blocked by the proxy” (class `error`), still one row, form values kept (`title=<script>alert(1)</script>`, `category=printer`, `priority=high`, `description=Brak wydruku z kolejki.`), no dialog and no page exception (`dialogs: []`).
- Edge b): the filter request `/api/tickets?search=e39a69&limit=50&offset=0` returned 200 and the list has exactly the step-1 ticket; the control search `zzz-no-match` shows „Brak zgłoszeń.”.
- Observation (not part of the verdict): after a successful list reload the old error text stays in `#message` („Request blocked by the proxy” remains visible after edge b), because `loadTickets` (frontend/app.js:193-202) never calls `showMessage`. The request status was therefore read from the resource timing entries.

## FE-03: Agent handles the ticket

```
[FE-03 precondition 2: click Wyloguj]
action: {"op":"click","scope":"#user-bar","text":"Wyloguj","wait":1000}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Wylogowano","messageClass":"success","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-03 precondition 3: fill Login (helpdesk)]
action: {"op":"fill","form":"#login-form","label":"Login","text":"helpdesk"}
state:  {"ok":true,"result":{"filled":"#login-form \"Login\"","length":8,"fromFile":false}}

[FE-03 precondition 3: fill Hasło (helpdesk, from file)]
action: {"op":"fill","form":"#login-form","label":"Hasło","file":"$RUN/pw.helpdesk"}
state:  {"ok":true,"result":{"filled":"#login-form \"Hasło\"","length":30,"fromFile":true}}

[FE-03 precondition 3: click Zaloguj]
action: {"op":"click","scope":"#login-form","text":"Zaloguj","wait":1500}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"","messageClass":"","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: Piotr Serwisant (agent Helpdesk)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Otwarte | QA Final Owner | — | 27.11.2026, 23:52:52","3 | Migający monitor | Monitor | Niski | Otwarte | Anna Nowak | — | 27.11.2026, 23:50:58","2 | Drukarka zacina papier | Drukarka | Średni | W realizacji | Jan Kowalski | Piotr Serwisant | 27.11.2026, 23:50:58","1 | Laptop nie uruchamia się po aktualizacji | Laptop | Wysoki | Otwarte | Jan Kowalski | — | 27.11.2026, 23:50:58"],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-03 step 1: open the FE-02 ticket (click the row)]
action: {"op":"clickRow","title":"Drukarka nie drukuje e39a69","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"","messageClass":"","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: Piotr Serwisant (agent Helpdesk)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Otwarte | QA Final Owner | — | 27.11.2026, 23:52:52","3 | Migający monitor | Monitor | Niski | Otwarte | Anna Nowak | — | 27.11.2026, 23:50:58","2 | Drukarka zacina papier | Drukarka | Średni | W realizacji | Jan Kowalski | Piotr Serwisant | 27.11.2026, 23:50:58","1 | Laptop nie uruchamia się po aktualizacji | Laptop | Wysoki | Otwarte | Jan Kowalski | — | 27.11.2026, 23:50:58"],"detailHeading":"#4 Drukarka nie drukuje e39a69","statusSelect":true,"assignButton":true}}

[FE-03 step 2: click Przypisz do mnie]
action: {"op":"click","scope":"#ticket-detail","text":"Przypisz do mnie","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Zgłoszenie przypisane do Ciebie","messageClass":"success","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: Piotr Serwisant (agent Helpdesk)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Otwarte | QA Final Owner | Piotr Serwisant | 27.11.2026, 23:52:52","3 | Migający monitor | Monitor | Niski | Otwarte | Anna Nowak | — | 27.11.2026, 23:50:58","2 | Drukarka zacina papier | Drukarka | Średni | W realizacji | Jan Kowalski | Piotr Serwisant | 27.11.2026, 23:50:58","1 | Laptop nie uruchamia się po aktualizacji | Laptop | Wysoki | Otwarte | Jan Kowalski | — | 27.11.2026, 23:50:58"],"detailHeading":"#4 Drukarka nie drukuje e39a69","statusSelect":true,"assignButton":true}}

[FE-03 step 3: choose W realizacji]
action: {"op":"selectId","id":"status-select","option":"W realizacji"}
state:  {"ok":true,"result":{"selected":"in_progress=W realizacji"}}

[FE-03 step 3: click Zmień status]
action: {"op":"click","scope":"#ticket-detail","text":"Zmień status","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Status zmieniony","messageClass":"success","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: Piotr Serwisant (agent Helpdesk)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | W realizacji | QA Final Owner | Piotr Serwisant | 27.11.2026, 23:52:52","3 | Migający monitor | Monitor | Niski | Otwarte | Anna Nowak | — | 27.11.2026, 23:50:58","2 | Drukarka zacina papier | Drukarka | Średni | W realizacji | Jan Kowalski | Piotr Serwisant | 27.11.2026, 23:50:58","1 | Laptop nie uruchamia się po aktualizacji | Laptop | Wysoki | Otwarte | Jan Kowalski | — | 27.11.2026, 23:50:58"],"detailHeading":"#4 Drukarka nie drukuje e39a69","statusSelect":true,"assignButton":true}}

[FE-03 step 4: choose Rozwiązane]
action: {"op":"selectId","id":"status-select","option":"Rozwiązane"}
state:  {"ok":true,"result":{"selected":"resolved=Rozwiązane"}}

[FE-03 step 4: click Zmień status]
action: {"op":"click","scope":"#ticket-detail","text":"Zmień status","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Status zmieniony","messageClass":"success","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: Piotr Serwisant (agent Helpdesk)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Rozwiązane | QA Final Owner | Piotr Serwisant | 27.11.2026, 23:52:52","3 | Migający monitor | Monitor | Niski | Otwarte | Anna Nowak | — | 27.11.2026, 23:50:58","2 | Drukarka zacina papier | Drukarka | Średni | W realizacji | Jan Kowalski | Piotr Serwisant | 27.11.2026, 23:50:58","1 | Laptop nie uruchamia się po aktualizacji | Laptop | Wysoki | Otwarte | Jan Kowalski | — | 27.11.2026, 23:50:58"],"detailHeading":"#4 Drukarka nie drukuje e39a69","statusSelect":true,"assignButton":true}}

[FE-03 step 5: choose Zamknięte]
action: {"op":"selectId","id":"status-select","option":"Zamknięte"}
state:  {"ok":true,"result":{"selected":"closed=Zamknięte"}}

[FE-03 step 5: click Zmień status]
action: {"op":"click","scope":"#ticket-detail","text":"Zmień status","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Status zmieniony","messageClass":"success","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: Piotr Serwisant (agent Helpdesk)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Zamknięte | QA Final Owner | Piotr Serwisant | 27.11.2026, 23:52:52","3 | Migający monitor | Monitor | Niski | Otwarte | Anna Nowak | — | 27.11.2026, 23:50:58","2 | Drukarka zacina papier | Drukarka | Średni | W realizacji | Jan Kowalski | Piotr Serwisant | 27.11.2026, 23:50:58","1 | Laptop nie uruchamia się po aktualizacji | Laptop | Wysoki | Otwarte | Jan Kowalski | — | 27.11.2026, 23:50:58"],"detailHeading":"#4 Drukarka nie drukuje e39a69","statusSelect":true,"assignButton":true}}

[FE-03 edge a: choose Otwarte on the closed ticket]
action: {"op":"selectId","id":"status-select","option":"Otwarte"}
state:  {"ok":true,"result":{"selected":"open=Otwarte"}}

[FE-03 edge a: click Zmień status]
action: {"op":"click","scope":"#ticket-detail","text":"Zmień status","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Invalid status transition: closed -> open","messageClass":"error","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: Piotr Serwisant (agent Helpdesk)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Zamknięte | QA Final Owner | Piotr Serwisant | 27.11.2026, 23:52:52","3 | Migający monitor | Monitor | Niski | Otwarte | Anna Nowak | — | 27.11.2026, 23:50:58","2 | Drukarka zacina papier | Drukarka | Średni | W realizacji | Jan Kowalski | Piotr Serwisant | 27.11.2026, 23:50:58","1 | Laptop nie uruchamia się po aktualizacji | Laptop | Wysoki | Otwarte | Jan Kowalski | — | 27.11.2026, 23:50:58"],"detailHeading":"#4 Drukarka nie drukuje e39a69","statusSelect":true,"assignButton":true}}

[FE-03 edge a: badge in the detail and in the list]
action: {"op":"eval","expr":"({detail: document.querySelector(\"#ticket-detail .status\").textContent, list: [...document.querySelectorAll(\"#ticket-list tr\")].filter((tr) => tr.textContent.includes(\"Drukarka\")).map((tr) => tr.children[4].textContent)})"}
state:  {"ok":true,"result":{"value":{"detail":"Zamknięte","list":["Zamknięte","W realizacji"]}}}

[FE-03 edge b: agent list (snapshot)]
action: {"op":"snap"}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Invalid status transition: closed -> open","messageClass":"error","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: Piotr Serwisant (agent Helpdesk)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Zamknięte | QA Final Owner | Piotr Serwisant | 27.11.2026, 23:52:52","3 | Migający monitor | Monitor | Niski | Otwarte | Anna Nowak | — | 27.11.2026, 23:50:58","2 | Drukarka zacina papier | Drukarka | Średni | W realizacji | Jan Kowalski | Piotr Serwisant | 27.11.2026, 23:50:58","1 | Laptop nie uruchamia się po aktualizacji | Laptop | Wysoki | Otwarte | Jan Kowalski | — | 27.11.2026, 23:50:58"],"detailHeading":"#4 Drukarka nie drukuje e39a69","statusSelect":true,"assignButton":true}}

[FE-03 edge b: row count]
action: {"op":"eval","expr":"document.querySelectorAll(\"#ticket-list tr\").length"}
state:  {"ok":true,"result":{"value":4}}

```

Result FE-03: **Pass**.
- Precondition: „Wylogowano”; after sign-in the user bar is „Zalogowano: Piotr Serwisant (agent Helpdesk)”.
- Step 2: „Zgłoszenie przypisane do Ciebie” (assignee `Piotr Serwisant`). Steps 3–5: „Status zmieniony” each; the row status went `W realizacji` → `Rozwiązane` → `Zamknięte`.
- Edge a): „Invalid status transition: closed -> open”; the badge in the detail and in the list stays `Zamknięte`.
- Edge b): the agent list has 4 rows (3 seeded tickets and the FE-02 ticket).

## FE-04: Session ended outside the UI

```
[FE-04 precondition: signed in as helpdesk (snapshot)]
action: {"op":"snap"}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Invalid status transition: closed -> open","messageClass":"error","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: Piotr Serwisant (agent Helpdesk)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Zamknięte | QA Final Owner | Piotr Serwisant | 27.11.2026, 23:52:52","3 | Migający monitor | Monitor | Niski | Otwarte | Anna Nowak | — | 27.11.2026, 23:50:58","2 | Drukarka zacina papier | Drukarka | Średni | W realizacji | Jan Kowalski | Piotr Serwisant | 27.11.2026, 23:50:58","1 | Laptop nie uruchamia się po aktualizacji | Laptop | Wysoki | Otwarte | Jan Kowalski | — | 27.11.2026, 23:50:58"],"detailHeading":"#4 Drukarka nie drukuje e39a69","statusSelect":true,"assignButton":true}}

[FE-04 step 1: tab.evaluate fetch logout]
action: {"op":"eval","expr":"fetch(\"/api/auth/logout\", {method: \"POST\", credentials: \"include\"}).then(r => r.status)"}
state:  {"ok":true,"result":{"value":200}}

[FE-04 step 2: click Filtruj]
action: {"op":"click","scope":"#filter-form","text":"Filtruj","wait":1200}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Sesja wygasła lub została zakończona — zaloguj się ponownie.","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-04 edge a: reload]
action: {"op":"reload"}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"","messageClass":"","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-04 edge b: fill Login (helpdesk)]
action: {"op":"fill","form":"#login-form","label":"Login","text":"helpdesk"}
state:  {"ok":true,"result":{"filled":"#login-form \"Login\"","length":8,"fromFile":false}}

[FE-04 edge b: fill Hasło (helpdesk, from file)]
action: {"op":"fill","form":"#login-form","label":"Hasło","file":"$RUN/pw.helpdesk"}
state:  {"ok":true,"result":{"filled":"#login-form \"Hasło\"","length":30,"fromFile":true}}

[FE-04 edge b: click Zaloguj]
action: {"op":"click","scope":"#login-form","text":"Zaloguj","wait":1500}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"","messageClass":"","authViewVisible":false,"appViewVisible":true,"userBar":"Zalogowano: Piotr Serwisant (agent Helpdesk)","rows":["4 | Drukarka nie drukuje e39a69 | Drukarka | Wysoki | Zamknięte | QA Final Owner | Piotr Serwisant | 27.11.2026, 23:52:52","3 | Migający monitor | Monitor | Niski | Otwarte | Anna Nowak | — | 27.11.2026, 23:50:58","2 | Drukarka zacina papier | Drukarka | Średni | W realizacji | Jan Kowalski | Piotr Serwisant | 27.11.2026, 23:50:58","1 | Laptop nie uruchamia się po aktualizacji | Laptop | Wysoki | Otwarte | Jan Kowalski | — | 27.11.2026, 23:50:58"],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-04 edge b: click Wyloguj]
action: {"op":"click","scope":"#user-bar","text":"Wyloguj","wait":1000}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Wylogowano","messageClass":"success","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-04 edge b: fetch /api/auth/me from the page]
action: {"op":"eval","expr":"fetch(\"/api/auth/me\", {credentials: \"include\"}).then(r => r.status)"}
state:  {"ok":true,"result":{"value":401}}

```

Result FE-04: **Pass**.
- Step 1: the page `fetch` of `/api/auth/logout` returned 200. Step 2: after „Filtruj” the auth view is shown with „Sesja wygasła lub została zakończona — zaloguj się ponownie.”.
- Edge a): after the reload the auth view is shown (`authViewVisible` true, `userBar` null).
- Edge b): sign-in and „Wyloguj” → „Wylogowano”; then `fetch('/api/auth/me')` returned 401.

## FE-05: CSP enforced by the proxy header

```
[FE-05 precondition: / is loaded (reload)]
action: {"op":"reload"}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"","messageClass":"","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-05 steps 1-5: one tab.evaluate]
action: {"op":"eval","expr":"(async () => { const violations = []; let evalError = null, fetchError = null; document.addEventListener('securitypolicyviolation', (e) => violations.push(e.violatedDirective)); const s = document.createElement('script'); s.textContent = 'window.__cspProbe = 1'; document.body.append(s); try { eval('1') } catch (e) { evalError = e.name } try { await fetch('https://example.com/') } catch (e) { fetchError = e.name } await new Promise((r) => setTimeout(r, 500)); return {cspProbe: typeof window.__cspProbe, violations, evalError, fetchError}; })()"}
state:  {"ok":true,"result":{"value":{"cspProbe":"undefined","violations":["script-src-elem","script-src-elem","connect-src","connect-src"],"evalError":null,"fetchError":"TypeError"}}}

[FE-05 edge a: meta CSP content]
action: {"op":"eval","expr":"document.querySelector(\"meta[http-equiv=\\\"Content-Security-Policy\\\"]\").content"}
state:  {"ok":true,"result":{"value":"default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'"}}

[FE-05 edge b: HEAD / headers]
action: {"op":"eval","expr":"fetch(\"/\", {method: \"HEAD\"}).then(r => ({status: r.status, xfo: r.headers.get(\"x-frame-options\"), csp: r.headers.get(\"content-security-policy\")}))"}
state:  {"ok":true,"result":{"value":{"status":200,"xfo":"DENY","csp":"default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"}}}

[FE-05 steps 1-5 repeated with step 3 also executed from a timer callback (page-owned task)]
action: {"op":"eval","expr":"(async () => { const violations = []; let evalError = null, fetchError = null, viaTimer = null; document.addEventListener('securitypolicyviolation', (e) => violations.push(e.violatedDirective)); const s = document.createElement('script'); s.textContent = 'window.__cspProbe2 = 1'; document.body.append(s); setTimeout(() => { try { eval('1'); viaTimer = 'no error' } catch (e) { viaTimer = e.name } }, 0); try { eval('1') } catch (e) { evalError = e.name } try { await fetch('https://example.com/') } catch (e) { fetchError = e.name } await new Promise((r) => setTimeout(r, 500)); return {cspProbe2: typeof window.__cspProbe2, violations, evalErrorInsideEvaluate: evalError, evalErrorInTimerCallback: viaTimer, fetchError}; })()"}
state:  {"ok":true,"result":{"value":{"cspProbe2":"undefined","violations":["script-src-elem","script-src-elem","connect-src","connect-src","script-src","script-src"],"evalErrorInsideEvaluate":null,"evalErrorInTimerCallback":"EvalError","fetchError":"TypeError"}}}

# Supplement added in review round 1 (note on `Runtime.evaluate`): run in the browser session of the FE-06 re-run, on the fresh stack, date 2026-11-28, host local time.

[FE-05 supplement: reload /]
at:     00:12:17.208 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"goto","url":"http://patchpoint.localhost:28080/"}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"","messageClass":"","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-05 supplement: eval inside default Runtime.evaluate]
at:     00:12:18.418 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"eval","expr":"(() => { try { eval('1'); return 'no error' } catch (e) { return e.name } })()"}
state:  {"ok":true,"result":{"value":"no error"}}

[FE-05 supplement: eval inside Runtime.evaluate with allowUnsafeEvalBlockedByCSP=false]
at:     00:12:18.418 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"evalNoUnsafeEval","expr":"(() => { try { eval('1'); return 'no error' } catch (e) { return e.name } })()"}
state:  {"ok":true,"result":{"value":"EvalError"}}

```

Result FE-05: **Pass** (with the method note below).
- `window.__cspProbe` is `undefined` (`cspProbe: "undefined"`). Violated directives: `script-src-elem` (the injected inline `<script>`), `connect-src` (the fetch to example.com), and, in the second run, `script-src` (the `eval`). Every directive is reported twice [INFERENCE: once for the header policy and once for the `<meta>` policy].
- `fetchError` is `TypeError`.
- `evalError` — method note: in the first run (steps 1–5 literally as in the plan, `eval('1')` written inside the `Runtime.evaluate` expression) `evalError` is `null`. Mechanism: the CDP command `Runtime.evaluate` has the parameter `allowUnsafeEvalBlockedByCSP`, which defaults to true [INFERENCE: default taken from the CDP documentation as remembered, not looked up here], so `eval` called from inside the evaluated expression is allowed even though the page's CSP forbids `unsafe-eval`. Checked in review round 1 (supplement records above, same page `/`): the same `eval('1')` expression returns `"no error"` with the default and throws `EvalError` when the evaluation is sent with `allowUnsafeEvalBlockedByCSP: false`. The step executed from a timer callback, i.e. a page-owned task, throws `EvalError` and reports the `script-src` violation (second run, `evalErrorInTimerCallback: "EvalError"`). The `EvalError` of the second run is taken as the result of the page's CSP; `unsafe-eval` is absent from both policies (edge a and b).
- Edge a): the meta content is `default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'` (contains `connect-src 'self'`).
- Edge b): `HEAD /` → 200, `x-frame-options: DENY`, `content-security-policy` ends with `frame-ancestors 'none'`.

## FE-06: Login rate limit and lockout in the UI

**Re-run in review round 1.** The first FE-06 record of this file (run `$SFX` = `e39a69`) contained only the precondition snapshot and the two edges; the main step (filling Login/Hasło, the 7 `Zaloguj` clicks with their `#message` states and the resource-timing read-out) was not recorded, and its raw driver output had been deleted with `$RUN`. That section was therefore replaced by the complete record below. FE-06 was run again, from scratch, on a **fresh** `patchpoint-final` stack (new volume, so the proxy rate-limit zone and the `login_failures` table were empty) with a new suffix `$SFX` = `eb8ddf`:

- Precondition (FE-01 owner): the owner `qa.final.eb8ddf.owner` was registered through the UI form in the same browser session (`„Zarejestruj konto”`, after a 7 s pacing sleep), then the driver waited 65 s so that the registration did not count against the `patchpoint_auth` zone, reloaded `/` and started FE-06 (itself unpaced, as the plan requires).
- Method: same engine and approach as in "How the browser was driven" (Chromium `157.0.8103.79`, headless, real mouse events, text typed through `Input.insertText`, passwords read from files under `$RUN`), with a **new** throwaway Node/CDP driver (`$RUN/drive.mjs`, dependency-free, deleted at the end of the task). The OMP `browser`/`eval` global was again not available (this agent has no `eval` tool). Differences from the first driver: every record carries an `at:` line, and the `click` op waits until Chromium reports the response of the `/api/auth/*` request it triggered (`Network.responseReceived`) plus 150 ms, so `#message` is read after the page handler ran. `authRequestsSinceLastRecord` in a click state lists those requests with `status`, `sentAt` and `receivedAt`.
- Timestamps: all times are the host's local clock, `HH:MM:SS.mmm` (date 2026-11-28, i.e. after midnight). `at:` = start of the action in the driver; `clickedAt` = the moment of the mouse press; `sentAt`/`receivedAt` = `Network.requestWillBeSent` / `Network.responseReceived` as seen by the driver. `sleep` records show the pacing (`ms`).
- The login form's password field keeps its value after a failed submit, so the 7 clicks need no refill. The Login field was filled once.
- Passwords: the owner's password and `Wrong-Password-12345` were read from files; the `form` records omit the password fields.

```
[precondition: goto /]
at:     00:09:25.964 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"goto","url":"http://patchpoint.localhost:28080/"}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"","messageClass":"","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[precondition: fill Login (owner)]
at:     00:09:27.188 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"fill","form":"#register-form","text":"qa.final.eb8ddf.owner","field":"Login"}
state:  {"ok":true,"result":{"filled":"#register-form \"Login\"","length":21,"fromFile":false}}

[precondition: fill Imię i nazwisko]
at:     00:09:27.193 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"fill","form":"#register-form","text":"QA Final Owner","field":"Imię i nazwisko"}
state:  {"ok":true,"result":{"filled":"#register-form \"Imię i nazwisko\"","length":14,"fromFile":false}}

[precondition: fill Dział]
at:     00:09:27.213 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"fill","form":"#register-form","text":"QA","field":"Dział"}
state:  {"ok":true,"result":{"filled":"#register-form \"Dział\"","length":2,"fromFile":false}}

[precondition: fill Hasło (from file)]
at:     00:09:27.230 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"fill","form":"#register-form","file":"$RUN/pw.qa.final.eb8ddf.owner","field":"Hasło"}
state:  {"ok":true,"result":{"filled":"#register-form \"Hasło\"","length":27,"fromFile":true}}

[precondition: form values before submit (passwords omitted)]
at:     00:09:27.247 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"form","form":"#register-form"}
state:  {"ok":true,"result":{"form":["username=qa.final.eb8ddf.owner","full_name=QA Final Owner","department=QA"]}}

[precondition: pacing sleep before the register submit]
at:     00:09:27.249 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"sleep","ms":7000}
state:  {"ok":true,"result":{"slept_ms":7000}}

[precondition: click Zarejestruj konto]
at:     00:09:34.256 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"click","scope":"#register-form","text":"Zarejestruj konto","expectRequests":1}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Konto utworzone — możesz się zalogować","messageClass":"success","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false,"clickedAt":"00:09:34.257","authRequestsSinceLastRecord":[{"path":"/api/auth/register","status":201,"sentAt":"00:09:34.261","receivedAt":"00:09:34.308"}]}}

[precondition: wait 65 s so that the proxy rate-limit zone is clean for FE-06]
at:     00:09:34.462 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"sleep","ms":65000}
state:  {"ok":true,"result":{"slept_ms":65000}}

[FE-06 precondition: reload, auth view shown]
at:     00:10:39.526 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"goto","url":"http://patchpoint.localhost:28080/"}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"","messageClass":"","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-06 precondition: owner exists (registration above); snapshot]
at:     00:10:40.737 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"snap"}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"","messageClass":"","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false}}

[FE-06 step: fill Login (owner)]
at:     00:10:40.737 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"fill","form":"#login-form","text":"qa.final.eb8ddf.owner","field":"Login"}
state:  {"ok":true,"result":{"filled":"#login-form \"Login\"","length":21,"fromFile":false}}

[FE-06 step: fill Hasło (Wrong-Password-12345, from file)]
at:     00:10:40.743 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"fill","form":"#login-form","file":"$RUN/pw.wrong","field":"Hasło"}
state:  {"ok":true,"result":{"filled":"#login-form \"Hasło\"","length":20,"fromFile":true}}

[FE-06 step: form values before the clicks (password omitted)]
at:     00:10:40.761 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"form","form":"#login-form"}
state:  {"ok":true,"result":{"form":["username=qa.final.eb8ddf.owner"]}}

[FE-06 step: submit 1 of 7 (click Zaloguj, no pause)]
at:     00:10:40.763 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"click","scope":"#login-form","text":"Zaloguj","expectRequests":1}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Invalid username or password","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false,"clickedAt":"00:10:40.764","authRequestsSinceLastRecord":[{"path":"/api/auth/login","status":401,"sentAt":"00:10:40.777","receivedAt":"00:10:40.902"}]}}

[FE-06 step: submit 2 of 7 (click Zaloguj, no pause)]
at:     00:10:41.078 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"click","scope":"#login-form","text":"Zaloguj","expectRequests":1}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Invalid username or password","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false,"clickedAt":"00:10:41.079","authRequestsSinceLastRecord":[{"path":"/api/auth/login","status":401,"sentAt":"00:10:41.081","receivedAt":"00:10:41.198"}]}}

[FE-06 step: submit 3 of 7 (click Zaloguj, no pause)]
at:     00:10:41.385 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"click","scope":"#login-form","text":"Zaloguj","expectRequests":1}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Invalid username or password","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false,"clickedAt":"00:10:41.385","authRequestsSinceLastRecord":[{"path":"/api/auth/login","status":401,"sentAt":"00:10:41.388","receivedAt":"00:10:41.501"}]}}

[FE-06 step: submit 4 of 7 (click Zaloguj, no pause)]
at:     00:10:41.688 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"click","scope":"#login-form","text":"Zaloguj","expectRequests":1}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Invalid username or password","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false,"clickedAt":"00:10:41.688","authRequestsSinceLastRecord":[{"path":"/api/auth/login","status":401,"sentAt":"00:10:41.690","receivedAt":"00:10:41.799"}]}}

[FE-06 step: submit 5 of 7 (click Zaloguj, no pause)]
at:     00:10:41.991 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"click","scope":"#login-form","text":"Zaloguj","expectRequests":1}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Invalid username or password","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false,"clickedAt":"00:10:41.992","authRequestsSinceLastRecord":[{"path":"/api/auth/login","status":401,"sentAt":"00:10:41.994","receivedAt":"00:10:42.103"}]}}

[FE-06 step: submit 6 of 7 (click Zaloguj, no pause)]
at:     00:10:42.297 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"click","scope":"#login-form","text":"Zaloguj","expectRequests":1}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Too many failed login attempts. Try again later.","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false,"clickedAt":"00:10:42.297","authRequestsSinceLastRecord":[{"path":"/api/auth/login","status":429,"sentAt":"00:10:42.299","receivedAt":"00:10:42.308"}]}}

[FE-06 step: submit 7 of 7 (click Zaloguj, no pause)]
at:     00:10:42.500 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"click","scope":"#login-form","text":"Zaloguj","expectRequests":1}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Too many requests, try again later","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false,"clickedAt":"00:10:42.501","authRequestsSinceLastRecord":[{"path":"/api/auth/login","status":429,"sentAt":"00:10:42.503","receivedAt":"00:10:42.509"}]}}

[FE-06 step: statuses of all login requests from resource timing]
at:     00:10:42.704 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"eval","expr":"performance.getEntriesByType(\"resource\").filter((e) => e.name.endsWith(\"/api/auth/login\")).map((e) => e.responseStatus)"}
state:  {"ok":true,"result":{"value":[401,401,401,401,401,429,429]}}

[FE-06 step: any 'Błąd serwera' in #message?]
at:     00:10:42.705 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"eval","expr":"document.getElementById(\"message\").textContent.includes(\"Błąd serwera\")"}
state:  {"ok":true,"result":{"value":false}}

[FE-06 edge a: fill Hasło (correct password, from file)]
at:     00:10:42.706 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"fill","form":"#login-form","file":"$RUN/pw.qa.final.eb8ddf.owner","field":"Hasło"}
state:  {"ok":true,"result":{"filled":"#login-form \"Hasło\"","length":27,"fromFile":true}}

[FE-06 edge a: click Zaloguj immediately]
at:     00:10:42.710 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"click","scope":"#login-form","text":"Zaloguj","expectRequests":1}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Too many requests, try again later","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false,"clickedAt":"00:10:42.711","authRequestsSinceLastRecord":[{"path":"/api/auth/login","status":429,"sentAt":"00:10:42.726","receivedAt":"00:10:42.742"}]}}

[FE-06 edge a: status of that login request (resource timing)]
at:     00:10:42.928 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"eval","expr":"performance.getEntriesByType(\"resource\").filter((e) => e.name.endsWith(\"/api/auth/login\")).slice(-1).map((e) => e.responseStatus)"}
state:  {"ok":true,"result":{"value":[429]}}

[FE-06 edge b: fill Hasło (wrong, from file)]
at:     00:10:42.928 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"fill","form":"#login-form","file":"$RUN/pw.wrong","field":"Hasło"}
state:  {"ok":true,"result":{"filled":"#login-form \"Hasło\"","length":20,"fromFile":true}}

[FE-06 edge b: wait 65 s]
at:     00:10:42.944 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"sleep","ms":65000}
state:  {"ok":true,"result":{"slept_ms":65000}}

[FE-06 edge b: wrong attempt 1 of 5 (click Zaloguj)]
at:     00:11:47.947 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"click","scope":"#login-form","text":"Zaloguj","expectRequests":1}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Too many failed login attempts. Try again later.","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false,"clickedAt":"00:11:47.948","authRequestsSinceLastRecord":[{"path":"/api/auth/login","status":429,"sentAt":"00:11:47.957","receivedAt":"00:11:47.972"}]}}

[FE-06 edge b: pacing sleep 7 s before attempt 2]
at:     00:11:48.157 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"sleep","ms":7000}
state:  {"ok":true,"result":{"slept_ms":7000}}

[FE-06 edge b: wrong attempt 2 of 5 (click Zaloguj)]
at:     00:11:55.160 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"click","scope":"#login-form","text":"Zaloguj","expectRequests":1}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Too many failed login attempts. Try again later.","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false,"clickedAt":"00:11:55.160","authRequestsSinceLastRecord":[{"path":"/api/auth/login","status":429,"sentAt":"00:11:55.163","receivedAt":"00:11:55.172"}]}}

[FE-06 edge b: pacing sleep 7 s before attempt 3]
at:     00:11:55.364 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"sleep","ms":7000}
state:  {"ok":true,"result":{"slept_ms":7000}}

[FE-06 edge b: wrong attempt 3 of 5 (click Zaloguj)]
at:     00:12:02.366 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"click","scope":"#login-form","text":"Zaloguj","expectRequests":1}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Too many failed login attempts. Try again later.","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false,"clickedAt":"00:12:02.366","authRequestsSinceLastRecord":[{"path":"/api/auth/login","status":429,"sentAt":"00:12:02.369","receivedAt":"00:12:02.376"}]}}

[FE-06 edge b: pacing sleep 7 s before attempt 4]
at:     00:12:02.570 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"sleep","ms":7000}
state:  {"ok":true,"result":{"slept_ms":7000}}

[FE-06 edge b: wrong attempt 4 of 5 (click Zaloguj)]
at:     00:12:09.571 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"click","scope":"#login-form","text":"Zaloguj","expectRequests":1}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Too many failed login attempts. Try again later.","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false,"clickedAt":"00:12:09.572","authRequestsSinceLastRecord":[{"path":"/api/auth/login","status":429,"sentAt":"00:12:09.574","receivedAt":"00:12:09.588"}]}}

[FE-06 edge b: pacing sleep 7 s before attempt 5]
at:     00:12:09.775 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"sleep","ms":7000}
state:  {"ok":true,"result":{"slept_ms":7000}}

[FE-06 edge b: wrong attempt 5 of 5 (click Zaloguj)]
at:     00:12:16.775 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"click","scope":"#login-form","text":"Zaloguj","expectRequests":1}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Too many failed login attempts. Try again later.","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false,"clickedAt":"00:12:16.776","authRequestsSinceLastRecord":[{"path":"/api/auth/login","status":429,"sentAt":"00:12:16.779","receivedAt":"00:12:16.788"}]}}

[FE-06 edge b: fill Hasło (correct, from file)]
at:     00:12:16.980 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"fill","form":"#login-form","file":"$RUN/pw.qa.final.eb8ddf.owner","field":"Hasło"}
state:  {"ok":true,"result":{"filled":"#login-form \"Hasło\"","length":27,"fromFile":true}}

[FE-06 edge b: click Zaloguj with the correct password]
at:     00:12:16.989 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"click","scope":"#login-form","text":"Zaloguj","expectRequests":1}
state:  {"ok":true,"result":{"url":"http://patchpoint.localhost:28080/","message":"Too many failed login attempts. Try again later.","messageClass":"error","authViewVisible":true,"appViewVisible":false,"userBar":null,"rows":[],"detailHeading":null,"statusSelect":false,"assignButton":false,"clickedAt":"00:12:16.990","authRequestsSinceLastRecord":[{"path":"/api/auth/login","status":429,"sentAt":"00:12:17.006","receivedAt":"00:12:17.021"}]}}

[FE-06 edge b: network statuses of the last 6 login requests (resource timing)]
at:     00:12:17.207 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"eval","expr":"performance.getEntriesByType(\"resource\").filter((e) => e.name.endsWith(\"/api/auth/login\")).slice(-6).map((e) => e.responseStatus)"}
state:  {"ok":true,"result":{"value":[429,429,429,429,429,429]}}

[FE-06 edge b: any 'Błąd serwera' in #message?]
at:     00:12:17.208 (host local time, HH:MM:SS.mmm, action started)
action: {"op":"eval","expr":"document.getElementById(\"message\").textContent.includes(\"Błąd serwera\")"}
state:  {"ok":true,"result":{"value":false}}
```

Result FE-06: **Pass** (re-run; the earlier Pass is confirmed — statuses and messages are identical to the first run).
- Main step: seven submits within 1.74 s (first click 00:10:40.764, 7th click 00:10:42.501). Messages 1–5 are „Invalid username or password” (HTTP 401 each, `receivedAt` 00:10:40.902 … 00:10:42.103). Message 6 is „Too many failed login attempts. Try again later.” (HTTP 429 from the API: the lockout after 5 failures). Message 7 is „Too many requests, try again later” (HTTP 429; the text is the proxy's `@patchpoint_rate_limited` text, and the response came 6 ms after sending, `receivedAt` 00:10:42.509). The 7th message is one of the two 429 texts. Resource timing: `[401,401,401,401,401,429,429]`, identical to the Network log. `#message` does not contain „Błąd serwera” (`false`); no message other than the three allowed texts appeared.
- Edge a): the correct password right afterwards (00:10:42.711) → the auth view stays, no app view, `#message` = „Too many requests, try again later” (HTTP 429, proxy rate limit).
- Edge b): after the 65 s wait (00:10:42.944 → first attempt at 00:11:47.947) five wrong attempts at 00:11:47.948, 00:11:55.160, 00:12:02.366, 00:12:09.572 and 00:12:16.776 (spacing 7.21 s, 7.21 s, 7.21 s, 7.20 s — `clickedAt` values, including the 7 s pacing sleeps recorded above). Each shows „Too many failed login attempts. Try again later.” (HTTP 429 from the API; the lockout from the main step is still in force, 15 min). The correct password at 00:12:16.990 also shows „Too many failed login attempts. Try again later.” (HTTP 429 — the lockout check comes before the password check). Resource timing of the last 6 login requests: `[429,429,429,429,429,429]`. `#message` does not contain „Błąd serwera”.
- Not recorded by this driver: dialogs and console errors (the `quit` record of the first driver reported none for the first run; this driver does not collect them).

## Tab teardown

The page recorded no dialogs and no uncaught exceptions during the first session (FE-01 – FE-06 as first run); then the browser was closed (the `quit` op of the driver terminated Chromium; no `chromium` process remained). The FE-06 re-run session (and the FE-05 supplement) used the second driver, which does not collect dialogs and console errors; it closed the browser with `Browser.close` and no process with its profile directory remained (`pgrep -af chrome-profile` printed nothing).

```
{"ok":true,"result":{"dialogs":[],"consoleErrors":[]}}
{"ok":true,"result":{"bye":true}}
```
