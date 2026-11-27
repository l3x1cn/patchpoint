#!/usr/bin/env bash
# PoC regresji bezpieczeństwa PatchPoint. Działa na kodzie Fazy 1 (wyniki PODATNE)
# i Fazy 2 (wyniki NAPRAWIONE). Zmienne: API_URL, FRONTEND_DIR, opcjonalnie
# DB_PATH (plik SQLite uruchomionego API) i API_LOG (log uruchomionego API).
set -euo pipefail

for tool in curl jq python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Brak wymaganego narzędzia: $tool" >&2
    exit 2
  fi
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_URL="${API_URL:-http://127.0.0.1:8000}"
FRONTEND_DIR="${FRONTEND_DIR:-$SCRIPT_DIR/../frontend}"
DB_PATH="${DB_PATH:-}"
if [[ -n "$DB_PATH" && ! -f "$DB_PATH" ]]; then
  echo "DB_PATH nie wskazuje istniejącego pliku: $DB_PATH" >&2
  exit 2
fi
API_LOG="${API_LOG:-}"

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

BODY="$WORK/body"
HDR="$WORK/hdr"
STATUS=000

# req <METODA> <ścieżka> [argumenty curl...] — ustawia STATUS, $BODY i $HDR
req() {
  local method="$1" path="$2"
  shift 2
  STATUS=$(curl -s --noproxy '*' -o "$BODY" -D "$HDR" -w '%{http_code}' -X "$method" "$@" "$API_URL$path") || STATUS=000
}

# post_json <ścieżka> <json> [argumenty curl...]
post_json() {
  local path="$1" json="$2"
  shift 2
  req POST "$path" -H 'Content-Type: application/json' -d "$json" "$@"
}

creds() {
  jq -n --arg u "$1" --arg p "$2" '{username: $u, password: $p}'
}

fail_prepare() {
  echo "Przygotowanie nie powiodło się: $1" >&2
  exit 2
}

declare -A DESC RES EVI
ORDER=(W-01 W-02 W-03 W-04 W-05 W-06 W-07 W-08 W-09 W-10 W-11 W-12 W-13 W-14 W-15 W-16 W-17 W-18 SEC-017 SEC-020 SEC-021 RT-13)
DESC[W-01]="Gadatliwy błąd bazy"
DESC[W-02]="Komunikat SQLite przy zajętym loginie"
DESC[W-03]="Tryb debug i publiczna dokumentacja API"
DESC[W-04]="Szczegóły środowiska w /api/health"
DESC[W-05]="Enumeracja kont"
DESC[W-06]="Hash hasła w odpowiedzi API"
DESC[W-07]="Hasła MD5 bez soli"
DESC[W-08]="Przewidywalny token sesji"
DESC[W-09]="Sesje bez wygasania"
DESC[W-10]="Wylogowanie nie unieważnia sesji"
DESC[W-11]="Ciasteczko bez flag, token w JSON i Bearer"
DESC[W-12]="Konto domyślne, brak polityki haseł i limitu prób"
DESC[W-13]="CORS odbija dowolny Origin"
DESC[W-14]="SQL injection w wyszukiwaniu"
DESC[W-15]="Nadanie roli przy rejestracji"
DESC[W-16]="IDOR na zgłoszeniach"
DESC[W-17]="XSS przez innerHTML"
DESC[W-18]="Brak logów bezpieczeństwa"
DESC[SEC-017]="Brak limitów rozmiaru i paginacji"
DESC[SEC-020]="Tokeny sesji jawnie w bazie"
DESC[SEC-021]="Brak nagłówków bezpieczeństwa"
DESC[RT-13]="Nieobsłużony OverflowError (traceback)"

# fixed|vuln|skip <id> <dowód>
fixed() { RES[$1]="NAPRAWIONE"; EVI[$1]="$2"; }
vuln() { RES[$1]="PODATNE"; EVI[$1]="$2"; }
skip() { RES[$1]="POMINIĘTE"; EVI[$1]="$2"; }

# has_header <plik> <wyrażenie regularne (ERE, bez rozróżniania wielkości liter)>
has_header() { grep -qiE "$2" "$1"; }

# sqlite_value <zapytanie> <parametr> — pierwsza kolumna pierwszego wiersza (tylko odczyt)
sqlite_value() {
  python3 - "$DB_PATH" "$1" "$2" <<'PY'
import sqlite3
import sys

con = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
row = con.execute(sys.argv[2], (sys.argv[3],)).fetchone()
print(row[0] if row else "")
PY
}

# sessions_columns — nazwy kolumn tabeli sessions
sessions_columns() {
  python3 - "$DB_PATH" <<'PY'
import sqlite3
import sys

con = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
print(" ".join(row[1] for row in con.execute("PRAGMA table_info(sessions)")))
PY
}

# sessions_contain <token> — "yes", gdy jakakolwiek wartość tabeli sessions jest równa tokenowi
sessions_contain() {
  python3 - "$DB_PATH" "$1" <<'PY'
import sqlite3
import sys

con = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
found = any(str(value) == sys.argv[2] for row in con.execute("SELECT * FROM sessions") for value in row)
print("yes" if found else "no")
PY
}

cookie_from_jar() {
  awk -F'\t' '$6 == "session" { print $7 }' "$1"
}

echo "PatchPoint — kontrola regresji bezpieczeństwa"
echo "API_URL: $API_URL"
echo "FRONTEND_DIR: $FRONTEND_DIR"
echo "Data: $(date -Iseconds)"

# --- 1. Przygotowanie -------------------------------------------------------
SFX=$(python3 -c 'import secrets; print(secrets.token_hex(4))')
PASS=$(python3 -c 'import secrets; print("PoC-" + secrets.token_urlsafe(18))')
USER_A="poc.a.$SFX"
USER_B="poc.b.$SFX"
USER_C="poc.c.$SFX"
USER_D="poc.d.$SFX"
JAR_A="$WORK/jar-a"
JAR_B="$WORK/jar-b"

for pair in "$USER_A:PoC A" "$USER_B:PoC B" "$USER_C:PoC C" "$USER_D:PoC D"; do
  login="${pair%%:*}"
  name="${pair#*:}"
  payload=$(jq -n --arg u "$login" --arg p "$PASS" --arg n "$name" '{username: $u, password: $p, full_name: $n}')
  post_json /api/auth/register "$payload"
  [[ "$STATUS" == 201 ]] || fail_prepare "rejestracja $login zwróciła HTTP $STATUS"
done

post_json /api/auth/login "$(creds "$USER_A" "$PASS")" -c "$JAR_A"
[[ "$STATUS" == 200 ]] || fail_prepare "logowanie $USER_A zwróciło HTTP $STATUS"
cp "$HDR" "$WORK/hdr-a"
cp "$BODY" "$WORK/body-a"
post_json /api/auth/login "$(creds "$USER_B" "$PASS")" -c "$JAR_B"
[[ "$STATUS" == 200 ]] || fail_prepare "logowanie $USER_B zwróciło HTTP $STATUS"

new_ticket() {
  local jar="$1" title="$2"
  post_json /api/tickets "$(jq -n --arg t "$title" '{title: $t, description: "Zgłoszenie testowe PoC", category: "other"}')" -b "$jar"
  [[ "$STATUS" == 201 ]] || fail_prepare "utworzenie zgłoszenia zwróciło HTTP $STATUS"
  jq -r '.id' "$BODY"
}
TA=$(new_ticket "$JAR_A" "PoC zgłoszenie A")
TB=$(new_ticket "$JAR_B" "PoC zgłoszenie B")

TOKEN_A=$(jq -r 'if has("token") then .token else "" end' "$WORK/body-a")
if [[ -z "$TOKEN_A" ]]; then
  TOKEN_A=$(cookie_from_jar "$JAR_A")
fi
[[ -n "$TOKEN_A" ]] || fail_prepare "brak tokenu sesji użytkownika $USER_A"

# --- 2. W-04, W-03, SEC-021, W-13 ------------------------------------------
req GET /api/health
if jq -e 'keys == ["status"]' "$BODY" >/dev/null 2>&1; then
  fixed W-04 "odpowiedź ma tylko klucz status"
else
  vuln W-04 "klucze odpowiedzi: $(jq -r 'keys | join(",")' "$BODY" 2>/dev/null || echo '?')"
fi

if has_header "$HDR" '^x-content-type-options: *nosniff' \
  && has_header "$HDR" '^x-frame-options:' \
  && has_header "$HDR" '^content-security-policy:'; then
  fixed SEC-021 "są X-Content-Type-Options, X-Frame-Options i Content-Security-Policy"
else
  vuln SEC-021 "brak co najmniej jednego z nagłówków: X-Content-Type-Options, X-Frame-Options, Content-Security-Policy"
fi

docs_statuses=""
docs_open=0
for path in /docs /redoc /openapi.json; do
  req GET "$path"
  docs_statuses="$docs_statuses $path=$STATUS"
  if [[ "$STATUS" != 404 ]]; then
    docs_open=1
  fi
done
if ((docs_open == 0)); then
  fixed W-03 "dokumentacja wyłączona:$docs_statuses"
else
  vuln W-03 "dokumentacja dostępna:$docs_statuses"
fi

req OPTIONS /api/tickets -H 'Origin: http://evil.example' -H 'Access-Control-Request-Method: GET'
if has_header "$HDR" '^access-control-allow-origin: *http://evil\.example'; then
  vuln W-13 "preflight z Origin http://evil.example odbity (HTTP $STATUS)"
else
  fixed W-13 "preflight z Origin http://evil.example bez Access-Control-Allow-Origin (HTTP $STATUS)"
fi

# --- 3. W-06, W-07, W-08, W-09, W-11 ----------------------------------------
req GET /api/auth/me -b "$JAR_A"
ME_HASH=""
if jq -e 'has("password_hash")' "$BODY" >/dev/null 2>&1; then
  ME_HASH=$(jq -r '.password_hash' "$BODY")
  vuln W-06 "/api/auth/me zwraca password_hash"
else
  fixed W-06 "/api/auth/me bez klucza password_hash (HTTP $STATUS)"
fi

# shellcheck disable=SC2016 # literalny prefiks PHC "$argon2id$", bez rozwinięcia zmiennych
ARGON2_PREFIX='$argon2id$'
md5_of_pass=$(python3 -c 'import hashlib, sys; print(hashlib.md5(sys.argv[1].encode()).hexdigest())' "$PASS")
if [[ -n "$DB_PATH" ]]; then
  stored_hash=$(sqlite_value 'SELECT password_hash FROM users WHERE username = ?' "$USER_A")
  if [[ "$stored_hash" == "$ARGON2_PREFIX"* ]]; then
    fixed W-07 "users.password_hash zaczyna się od \$argon2id\$"
  elif [[ "$stored_hash" == "$md5_of_pass" ]]; then
    vuln W-07 "users.password_hash = md5(hasła), bez soli"
  else
    vuln W-07 "users.password_hash nie jest Argon2id"
  fi
elif [[ -z "$ME_HASH" ]]; then
  fixed W-07 "API nie zwraca hasha (bez DB_PATH nie sprawdzono bazy)"
elif [[ "$ME_HASH" == "$md5_of_pass" ]]; then
  vuln W-07 "hash z /api/auth/me = md5(hasła), bez soli"
elif [[ "$ME_HASH" == "$ARGON2_PREFIX"* ]]; then
  fixed W-07 "hash z /api/auth/me zaczyna się od \$argon2id\$"
else
  vuln W-07 "hash z /api/auth/me nie jest Argon2id"
fi

w08_rc=0
python3 - "$USER_A" "$TOKEN_A" <<'PY' || w08_rc=$?
import hashlib
import sys
import time

user, token = sys.argv[1], sys.argv[2]
now = int(time.time())
predictable = any(
    hashlib.md5(f"{user}:{moment}".encode()).hexdigest() == token
    for moment in range(now - 300, now + 5)
)
if predictable:
    sys.exit(1)
sys.exit(2 if len(token) < 43 else 0)
PY
case "$w08_rc" in
  0) fixed W-08 "token ma ${#TOKEN_A} znaków i nie pasuje do md5(login:czas)" ;;
  1) vuln W-08 "token = md5(login:czas)" ;;
  *) vuln W-08 "token krótszy niż 43 znaki (${#TOKEN_A})" ;;
esac

cookie_line=$(grep -i '^set-cookie: *session=' "$WORK/hdr-a" || true)
w09_columns=""
w09_ok=1
if ! grep -qi 'max-age=' <<<"$cookie_line"; then
  w09_ok=0
fi
if [[ -n "$DB_PATH" ]]; then
  w09_columns=$(sessions_columns)
  if [[ " $w09_columns " != *" expires_at "* ]]; then
    w09_ok=0
  fi
fi
if ((w09_ok == 1)); then
  fixed W-09 "Set-Cookie z Max-Age${DB_PATH:+, sessions ma expires_at}"
else
  # Szczegóły w zmiennej: nawiasy wewnątrz ${VAR:+...} wywalają parser bash w Semgrepie (błąd składni).
  w09_detail=""
  if [[ -n "$DB_PATH" ]]; then
    w09_detail=" lub expires_at w sessions (kolumny: $w09_columns)"
  fi
  vuln W-09 "brak Max-Age w Set-Cookie${w09_detail}"
fi

w11_problems=""
for flag in HttpOnly Secure SameSite=Strict; do
  if ! grep -qi "$flag" <<<"$cookie_line"; then
    w11_problems="$w11_problems brak-$flag"
  fi
done
if jq -e 'has("token")' "$WORK/body-a" >/dev/null 2>&1; then
  w11_problems="$w11_problems token-w-JSON"
fi
req GET /api/auth/me -H "Authorization: Bearer $TOKEN_A"
if [[ "$STATUS" != 401 ]]; then
  w11_problems="$w11_problems Bearer-HTTP-$STATUS"
fi
if [[ -z "$w11_problems" ]]; then
  fixed W-11 "ciasteczko HttpOnly, Secure, SameSite=Strict; brak tokenu w JSON; Bearer daje 401"
else
  vuln W-11 "problemy:$w11_problems"
fi

# --- 4. W-01, W-14, RT-13, SEC-017 ------------------------------------------
req GET /api/tickets -G --data-urlencode "search=O'Brien" -b "$JAR_A"
if [[ "$STATUS" != 500 ]] && ! grep -qiE '"query"|traceback' "$BODY"; then
  fixed W-01 "search=O'Brien daje HTTP $STATUS bez SQL i tracebacku"
else
  vuln W-01 "search=O'Brien daje HTTP $STATUS; ciało ujawnia SQL lub traceback"
fi

req GET /api/tickets -G --data-urlencode "search=') OR 1=1 OR ('" -b "$JAR_A"
w14_leak=no
if [[ "$STATUS" == 200 ]] && jq -e 'type == "array"' "$BODY" >/dev/null 2>&1; then
  if jq -e --argjson id "$TB" 'any(.[]; .id == $id)' "$BODY" >/dev/null 2>&1; then
    w14_leak=yes
  fi
  if [[ "$w14_leak" == no ]]; then
    fixed W-14 "HTTP 200, wynik nie zawiera cudzego zgłoszenia #$TB"
  else
    vuln W-14 "wstrzyknięty warunek zwrócił cudze zgłoszenie #$TB"
  fi
else
  vuln W-14 "HTTP $STATUS zamiast listy (fraza została zinterpretowana jako SQL)"
fi

req GET /api/tickets/99999999999999999999 -b "$JAR_A"
if [[ "$STATUS" == 422 ]]; then
  fixed RT-13 "identyfikator poza zakresem daje HTTP 422"
else
  vuln RT-13 "identyfikator 99999999999999999999 daje HTTP $STATUS zamiast 422"
fi

python3 - "$WORK" <<'PY'
import json
import pathlib
import sys

work = pathlib.Path(sys.argv[1])
long_title = {"title": "x" * 300, "description": "PoC", "category": "other"}
big_body = {"title": "PoC", "description": "a" * 70000, "category": "other"}
(work / "long-title.json").write_text(json.dumps(long_title), encoding="utf-8")
(work / "big-body.json").write_text(json.dumps(big_body), encoding="utf-8")
PY
req POST /api/tickets -H 'Content-Type: application/json' -d @"$WORK/long-title.json" -b "$JAR_A"
s_title=$STATUS
req GET /api/tickets -G --data-urlencode "limit=1000" -b "$JAR_A"
s_limit=$STATUS
req POST /api/tickets -H 'Content-Type: application/json' -d @"$WORK/big-body.json" -b "$JAR_A"
s_big=$STATUS
if [[ "$s_title" == 422 && "$s_limit" == 422 && "$s_big" == 413 ]]; then
  fixed SEC-017 "tytuł 300 znaków=$s_title, limit=1000=$s_limit, ciało 70 kB=$s_big"
else
  vuln SEC-017 "tytuł 300 znaków=$s_title (oczekiwano 422), limit=1000=$s_limit (422), ciało 70 kB=$s_big (413)"
fi

# --- 5. W-16 -----------------------------------------------------------------
req GET "/api/tickets/$TA" -b "$JAR_B"
s_read=$STATUS
post_json "/api/tickets/$TA/comments" '{"body":"Komentarz PoC użytkownika B"}' -b "$JAR_B"
s_comment=$STATUS
if [[ "$s_read" != 200 && "$s_comment" != 201 ]]; then
  fixed W-16 "cudze zgłoszenie: odczyt HTTP $s_read, komentarz HTTP $s_comment"
else
  vuln W-16 "cudze zgłoszenie: odczyt HTTP $s_read, komentarz HTTP $s_comment"
fi

# --- 6. W-02, W-15, W-12(b) -------------------------------------------------
dup_payload=$(jq -n --arg u "$USER_A" --arg p "$PASS" '{username: $u, password: $p, full_name: "PoC A"}')
post_json /api/auth/register "$dup_payload"
if [[ "$STATUS" == 409 ]] && ! grep -qiE 'constraint|users\.' "$BODY"; then
  fixed W-02 "ponowna rejestracja daje HTTP 409 bez szczegółów bazy"
else
  vuln W-02 "ponowna rejestracja daje HTTP $STATUS; ciało ujawnia szczegóły bazy lub status ≠ 409"
fi

agent_payload=$(jq -n --arg u "poc.f.$SFX" --arg p "$PASS" '{username: $u, password: $p, full_name: "PoC F", role: "agent"}')
post_json /api/auth/register "$agent_payload"
if [[ "$STATUS" == 201 ]] && jq -e '.role == "agent"' "$BODY" >/dev/null 2>&1; then
  vuln W-15 "rejestracja z role=agent utworzyła agenta (HTTP 201)"
else
  fixed W-15 "rejestracja z role=agent odrzucona lub bez roli agenta (HTTP $STATUS)"
fi

empty_payload=$(jq -n --arg u "poc.e.$SFX" '{username: $u, password: "", full_name: "PoC E"}')
post_json /api/auth/register "$empty_payload"
w12_empty=$STATUS

# --- 7. W-05 -----------------------------------------------------------------
post_json /api/auth/login "$(creds "poc.nobody.$SFX" "$PASS")"
s_unknown=$STATUS
b_unknown=$(cat "$BODY")
post_json /api/auth/login "$(creds "$USER_A" "zle-haslo-$SFX")"
s_badpass=$STATUS
b_badpass=$(cat "$BODY")
if [[ "$s_unknown" == "$s_badpass" && "$b_unknown" == "$b_badpass" ]]; then
  fixed W-05 "nieznany login i złe hasło: identyczne HTTP $s_unknown i ciało"
else
  vuln W-05 "nieznany login $s_unknown vs złe hasło $s_badpass"
fi

# --- 8. W-12(a), W-12(c) -----------------------------------------------------
post_json /api/auth/login "$(creds admin admin123)"
w12_admin=$STATUS
w12_last=000
for attempt in 1 2 3 4 5 6; do
  post_json /api/auth/login "$(creds "$USER_D" "zle-haslo-$attempt-$SFX")"
  w12_last=$STATUS
done
if [[ ("$w12_admin" == 401 || "$w12_admin" == 429) && "$w12_empty" == 422 && "$w12_last" == 429 ]]; then
  fixed W-12 "admin/admin123=$w12_admin, puste hasło przy rejestracji=$w12_empty, szósta zła próba=$w12_last"
else
  vuln W-12 "admin/admin123=$w12_admin (oczekiwano 401 lub 429), puste hasło przy rejestracji=$w12_empty (422), szósta zła próba=$w12_last (429)"
fi

# --- 9. W-10 -----------------------------------------------------------------
JAR_C="$WORK/jar-c"
post_json /api/auth/login "$(creds "$USER_C" "$PASS")" -c "$JAR_C"
[[ "$STATUS" == 200 ]] || fail_prepare "logowanie $USER_C zwróciło HTTP $STATUS"
TOKEN_C=$(jq -r 'if has("token") then .token else "" end' "$BODY")
if [[ -z "$TOKEN_C" ]]; then
  TOKEN_C=$(cookie_from_jar "$JAR_C")
fi
[[ -n "$TOKEN_C" ]] || fail_prepare "brak tokenu sesji użytkownika $USER_C"
req POST /api/auth/logout -b "$JAR_C"
s_logout=$STATUS
req GET /api/auth/me -H "Cookie: session=$TOKEN_C"
if [[ "$STATUS" == 401 ]]; then
  fixed W-10 "po wylogowaniu (HTTP $s_logout) stary token daje HTTP 401"
else
  vuln W-10 "po wylogowaniu (HTTP $s_logout) stary token nadal daje HTTP $STATUS"
fi

# --- 10. W-17, W-18, SEC-020 -------------------------------------------------
w17_problems=""
if grep -qF 'innerHTML' "$FRONTEND_DIR/app.js"; then
  w17_problems="$w17_problems innerHTML-w-app.js"
fi
if ! grep -qF 'Content-Security-Policy' "$FRONTEND_DIR/index.html"; then
  w17_problems="$w17_problems brak-CSP-w-index.html"
fi
if [[ -z "$w17_problems" ]]; then
  fixed W-17 "app.js bez innerHTML, index.html ma Content-Security-Policy"
else
  vuln W-17 "problemy:$w17_problems"
fi

if [[ -z "$API_LOG" ]]; then
  skip W-18 "brak API_LOG"
elif grep -qF '"event": "login_failed"' "$API_LOG"; then
  fixed W-18 "log API zawiera zdarzenie login_failed"
else
  vuln W-18 "log API nie zawiera zdarzeń bezpieczeństwa (login_failed)"
fi

if [[ -z "$DB_PATH" ]]; then
  skip SEC-020 "brak DB_PATH"
else
  columns=$(sessions_columns)
  contains=$(sessions_contain "$TOKEN_A")
  if [[ " $columns " == *" token_hash "* && "$contains" == no ]]; then
    fixed SEC-020 "sessions ma token_hash, a tokenu sesji nie ma w bazie jawnie"
  else
    vuln SEC-020 "sessions (kolumny: $columns), token jawnie w bazie: $contains"
  fi
fi

# --- Wyniki ------------------------------------------------------------------
echo
vulnerable=0
fixed_count=0
skipped=0
for id in "${ORDER[@]}"; do
  echo "[${RES[$id]}] $id ${DESC[$id]} — ${EVI[$id]}"
  case "${RES[$id]}" in
    PODATNE) vulnerable=$((vulnerable + 1)) ;;
    NAPRAWIONE) fixed_count=$((fixed_count + 1)) ;;
    *) skipped=$((skipped + 1)) ;;
  esac
done
echo
echo "Podsumowanie: podatne=$vulnerable, naprawione=$fixed_count, pominięte=$skipped"

if ((vulnerable > 0)); then
  exit 1
fi
exit 0
