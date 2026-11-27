#!/usr/bin/env bash
set -euo pipefail

for tool in curl jq; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Brak wymaganego narzędzia: $tool" >&2
    exit 2
  fi
done

if [[ -z "${DEMO_PASSWORD:-}" ]]; then
  echo "Ustaw DEMO_PASSWORD — hasło kont demo, takie samo jak PATCHPOINT_DEMO_PASSWORD uruchomionego API." >&2
  exit 2
fi

API_URL="${API_URL:-http://127.0.0.1:8000}"
WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

BODY="$WORKDIR/body.json"

echo "PatchPoint — demo end-to-end"
echo "API: $API_URL"
echo "Data: $(date -Iseconds)"

# Hasło nie trafia do argumentów żadnego procesu (/proc/<pid>/cmdline czyta każdy użytkownik):
# do jq idzie przez stdin z wbudowanego printf, a ciało żądania do curla przez stdin (@-).
login_payload() {
  printf '%s' "$DEMO_PASSWORD" | jq -Rsc --arg u "$1" '{username: $u, password: .}'
}

# request <oczekiwany_status> <słoik> <METODA> <ścieżka> [json]
request() {
  local expected="$1" jar="$2" method="$3" path="$4" payload="${5:-}"
  local args=(-s --noproxy '*' -o "$BODY" -w '%{http_code}' -X "$method" -b "$WORKDIR/$jar.txt" -c "$WORKDIR/$jar.txt")
  local status
  if [[ -n "$payload" ]]; then
    args+=(-H 'Content-Type: application/json' --data-binary @-)
    status=$(curl "${args[@]}" "$API_URL$path" <<<"$payload") || status="000"
  else
    status=$(curl "${args[@]}" "$API_URL$path" </dev/null) || status="000"
  fi
  echo "→ $method $path ($status)"
  if [[ "$status" != "$expected" ]]; then
    echo "BŁĄD: $method $path zwróciło $status, oczekiwano $expected"
    cat "$BODY" 2>/dev/null || true
    echo
    exit 1
  fi
}

TICKET_TITLE="Stacja dokująca nie wykrywa monitorów"

echo
echo "==> Krok 1: Sprawdzenie stanu API"
request 200 anon GET /api/health
jq -r '"status: \(.status)"' "$BODY"

echo
echo "==> Krok 2: Logowanie pracownika jan.kowalski"
request 200 jan POST /api/auth/login "$(login_payload jan.kowalski)"
jq -r '"Zalogowano: \(.user.full_name) (rola: \(.user.role))"' "$BODY"

echo
echo "==> Krok 3: Jan tworzy nowe zgłoszenie"
payload=$(jq -n --arg title "$TICKET_TITLE" \
  --arg description "Po podłączeniu laptopa do stacji dokującej oba monitory pozostają czarne." \
  '{title: $title, description: $description, category: "peripheral", priority: "high",
    asset_tag: "DOC-0310", location: "B-204"}')
request 201 jan POST /api/tickets "$payload"
TICKET_ID=$(jq -r '.id' "$BODY")
jq -r '"Zgłoszenie #\(.id), status: \(.status)"' "$BODY"

echo
echo "==> Krok 4: Jan pobiera swoją listę zgłoszeń"
request 200 jan GET /api/tickets
jq -r '"Liczba zgłoszeń Jana: \(length)"' "$BODY"
jq -r '.[] | "#\(.id) [\(.status)] \(.title)"' "$BODY"

echo
echo "==> Krok 5: Logowanie agenta helpdesk"
request 200 helpdesk POST /api/auth/login "$(login_payload helpdesk)"
HELPDESK_ID=$(jq -r '.user.id' "$BODY")
jq -r '"Zalogowano: \(.user.full_name) (rola: \(.user.role), id: \(.user.id))"' "$BODY"

echo
echo "==> Krok 6: Helpdesk pobiera wszystkie zgłoszenia"
request 200 helpdesk GET /api/tickets
jq -r '"Liczba wszystkich zgłoszeń: \(length)"' "$BODY"

echo
echo "==> Krok 7: Helpdesk podejmuje zgłoszenie i przypisuje je do siebie"
payload=$(jq -n --argjson assignee "$HELPDESK_ID" '{status: "in_progress", assignee_id: $assignee}')
request 200 helpdesk PATCH "/api/tickets/$TICKET_ID" "$payload"
jq -r '"status: \(.status), przypisany: \(.assignee_name)"' "$BODY"

echo
echo "==> Krok 8: Helpdesk dodaje komentarz"
payload=$(jq -n --arg body "Sprawdzam sterowniki stacji dokującej — proszę nie odłączać laptopa." '{body: $body}')
request 201 helpdesk POST "/api/tickets/$TICKET_ID/comments" "$payload"
jq -r '"Komentarz #\(.id) dodany przez: \(.author_name)"' "$BODY"

echo
echo "==> Krok 9: Jan sprawdza szczegóły zgłoszenia"
request 200 jan GET "/api/tickets/$TICKET_ID"
jq -r '"status: \(.status), przypisany: \(.assignee_name)"' "$BODY"
jq -r '.comments[] | "komentarz (\(.author_name)): \(.body)"' "$BODY"

echo
echo "==> Krok 10: Helpdesk rozwiązuje i zamyka zgłoszenie"
request 200 helpdesk PATCH "/api/tickets/$TICKET_ID" '{"status":"resolved"}'
request 200 helpdesk PATCH "/api/tickets/$TICKET_ID" '{"status":"closed"}'
jq -r '"Status końcowy: \(.status)"' "$BODY"

echo
# shellcheck disable=SC1111 # typograficzne cudzysłowy są częścią wypisywanego tekstu
echo "==> Krok 11: Jan wyszukuje zgłoszenia frazą „dokuj”"
request 200 jan GET "/api/tickets?search=dokuj"
jq -r '.[] | "trafienie: #\(.id) \(.title)"' "$BODY"
jq -e --argjson id "$TICKET_ID" 'any(.[]; .id == $id)' "$BODY" >/dev/null
echo "Nowe zgłoszenie #$TICKET_ID jest wśród wyników"

echo
echo "==> Krok 12: Jan wylogowuje się"
request 200 jan POST /api/auth/logout
jq -r '.message' "$BODY"
request 401 jan GET /api/auth/me
echo "Sesja zakończona (HTTP 401)"

echo
echo "DEMO ZAKOŃCZONE POWODZENIEM"
