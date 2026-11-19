#!/usr/bin/env bash
# Smoke obrazów i stosu compose w ustawieniach produkcyjnych: make stack-smoke i job build w CI
# (.github/workflows/ci.yml). Sprawdza oba obrazy, kontener API z PoC bezpieczeństwa oraz stos z compose.yaml
# (proxy z TLS i WAF przed API w sieci bez wyjścia). Wymaga: docker z compose, curl, jq, python3, openssl.
# Łączy się wyłącznie z pętlą zwrotną (127.0.0.1, patchpoint.localhost). Obrazy: PATCHPOINT_API_IMAGE i PATCHPOINT_PROXY_IMAGE (make images).
# Porty i stos: SMOKE_API_PORT, SMOKE_HTTP_PORT, SMOKE_HTTPS_PORT, SMOKE_PROJECT, SMOKE_SUBNET, SMOKE_PROXY_IP.
# Hasła i tokeny są losowe, nie trafiają do argumentów procesów, wyniku ani plików poza katalogiem tymczasowym.
set -euo pipefail

cd "$(dirname "$0")/.."

for tool in docker curl jq python3 openssl; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Brak wymaganego narzędzia: $tool" >&2
    exit 2
  fi
done
if ! docker compose version >/dev/null 2>&1; then
  echo "Brak docker compose (wymagane >= 2.24)." >&2
  exit 2
fi

export PATCHPOINT_API_IMAGE="${PATCHPOINT_API_IMAGE:-patchpoint-api:local}"
export PATCHPOINT_PROXY_IMAGE="${PATCHPOINT_PROXY_IMAGE:-patchpoint-proxy:local}"
SMOKE_API_PORT="${SMOKE_API_PORT:-18000}"
SMOKE_HTTP_PORT="${SMOKE_HTTP_PORT:-18080}"
SMOKE_HTTPS_PORT="${SMOKE_HTTPS_PORT:-18443}"
SMOKE_PROJECT="${SMOKE_PROJECT:-patchpoint-smoke}"
SMOKE_SUBNET="${SMOKE_SUBNET:-10.251.0.0/24}"
SMOKE_PROXY_IP="${SMOKE_PROXY_IP:-10.251.0.10}"
API_CONTAINER="patchpoint-smoke-api"

FAILURES=0
LOGS_PID=""
WORK=$(mktemp -d)

cleanup() {
  set +e
  if [[ -n "$LOGS_PID" ]]; then
    kill "$LOGS_PID" 2>/dev/null
  fi
  docker rm -f "$API_CONTAINER" >/dev/null 2>&1
  docker compose -p "$SMOKE_PROJECT" down -v >/dev/null 2>&1
  rm -rf "$WORK"
}
trap cleanup EXIT

ok() { echo "[OK] $1"; }
bad() {
  echo "[BŁĄD] $1"
  FAILURES=$((FAILURES + 1))
}

# die <opis> — błąd przygotowania: komunikat, ostatnie logi kontenerów i kod 2
die() {
  echo "Przygotowanie nie powiodło się: $1" >&2
  docker logs --tail 50 "$API_CONTAINER" >&2 2>&1 || true
  docker compose -p "$SMOKE_PROJECT" logs --tail 50 >&2 2>&1 || true
  exit 2
}

# Hasło demo i sufiks nazw: losowe, niewypisywane.
DEMO_PASSWORD="Smoke-$(python3 -c 'import secrets; print(secrets.token_urlsafe(18))')"
export DEMO_PASSWORD
export PATCHPOINT_DEMO_PASSWORD="$DEMO_PASSWORD"
SFX=$(python3 -c 'import secrets; print(secrets.token_hex(4))')

echo "PatchPoint — smoke obrazów i stosu compose"
echo "Obraz API: $PATCHPOINT_API_IMAGE"
echo "Obraz proxy: $PATCHPOINT_PROXY_IMAGE"
echo "Data: $(date -Iseconds)"

# --- Część 1. Obrazy ---------------------------------------------------------
echo
echo "==> Część 1: obrazy"

user=$(docker image inspect -f '{{.Config.User}}' "$PATCHPOINT_API_IMAGE") || die "brak obrazu $PATCHPOINT_API_IMAGE (make images)"
if [[ "$user" == "10001:10001" ]]; then ok "obraz API działa jako 10001:10001"; else bad "obraz API: użytkownik '$user', oczekiwano 10001:10001"; fi
user=$(docker image inspect -f '{{.Config.User}}' "$PATCHPOINT_PROXY_IMAGE") || die "brak obrazu $PATCHPOINT_PROXY_IMAGE (make images)"
if [[ "$user" == "nginx" ]]; then ok "obraz proxy działa jako nginx"; else bad "obraz proxy: użytkownik '$user', oczekiwano nginx"; fi

for image in "$PATCHPOINT_API_IMAGE" "$PATCHPOINT_PROXY_IMAGE"; do
  if docker image inspect -f '{{json .Config.Healthcheck.Test}}' "$image" | jq -e 'type == "array" and length > 0' >/dev/null 2>&1; then
    ok "obraz $image ma HEALTHCHECK"
  else
    bad "obraz $image nie ma HEALTHCHECK"
  fi
done

if docker run --rm --entrypoint python "$PATCHPOINT_API_IMAGE" -c 'import importlib.util, sys; sys.exit(0 if importlib.util.find_spec("pip") is None else 1)'; then
  ok "obraz API nie zawiera pip"
else
  bad "obraz API zawiera pip"
fi

# --- Część 2. Kontener API i PoC bezpieczeństwa ----------------------------------
echo
echo "==> Część 2: kontener API i PoC z Fazy 2"

mkdir -m 0700 "$WORK/data"
# --user hosta: PoC czyta plik bazy z katalogu tymczasowego. Hasło idzie ze środowiska (-e bez wartości).
docker run -d --name "$API_CONTAINER" --read-only --tmpfs /tmp --cap-drop ALL \
  --security-opt no-new-privileges:true --user "$(id -u):$(id -g)" \
  -v "$WORK/data:/data" -p "127.0.0.1:$SMOKE_API_PORT:8000" \
  -e PATCHPOINT_SEED_DEMO_DATA=true -e PATCHPOINT_DEMO_PASSWORD \
  "$PATCHPOINT_API_IMAGE" >/dev/null || die "nie udało się uruchomić kontenera API"
docker logs -f "$API_CONTAINER" >"$WORK/api.log" 2>&1 &
LOGS_PID=$!

ready=0
for _ in $(seq 1 60); do
  if curl -sf --noproxy '*' -o /dev/null "http://127.0.0.1:$SMOKE_API_PORT/api/health"; then
    ready=1
    break
  fi
  sleep 1
done
[[ "$ready" -eq 1 ]] || die "API nie odpowiada na /api/health w ciągu 60 s"

poc_status=0
API_URL="http://127.0.0.1:$SMOKE_API_PORT" DB_PATH="$WORK/data/patchpoint.db" API_LOG="$WORK/api.log" \
  ./scripts/security_check.sh >"$WORK/poc.txt" 2>&1 || poc_status=$?
poc_fixed=$(grep -c '^\[NAPRAWIONE\]' "$WORK/poc.txt" || true)
poc_summary=$(grep '^Podsumowanie:' "$WORK/poc.txt" || echo "Podsumowanie: brak")
if [[ "$poc_status" -eq 0 && "$poc_fixed" -eq 22 ]]; then
  ok "PoC Fazy 2 w kontenerze API: 22 × [NAPRAWIONE]"
else
  bad "PoC Fazy 2 w kontenerze API: kod $poc_status, [NAPRAWIONE]: $poc_fixed"
fi
echo "     $poc_summary"

if [[ "$(grep -cF "$DEMO_PASSWORD" "$WORK/api.log" || true)" -eq 0 ]]; then
  ok "log kontenera API nie zawiera hasła demo"
else
  bad "log kontenera API zawiera hasło demo"
fi

kill "$LOGS_PID" 2>/dev/null || true
wait "$LOGS_PID" 2>/dev/null || true
LOGS_PID=""
docker rm -f "$API_CONTAINER" >/dev/null 2>&1 || true

# --- Część 3. Stos compose (ustawienia produkcyjne) --------------------------------
echo
echo "==> Część 3: stos compose z proxy, WAF i TLS"

./scripts/dev_cert.sh "$WORK/tls" >/dev/null || die "nie udało się utworzyć certyfikatu deweloperskiego"
# printf jest poleceniem wbudowanym powłoki, więc hasło nie trafia do argumentów procesu.
(umask 077 && printf 'PATCHPOINT_SEED_DEMO_DATA=true\nPATCHPOINT_DEMO_PASSWORD=%s\n' "$DEMO_PASSWORD" >"$WORK/api.env")

export PATCHPOINT_DOMAIN=patchpoint.localhost
export PATCHPOINT_PUBLIC_ORIGINS="[\"https://patchpoint.localhost:$SMOKE_HTTPS_PORT\"]"
export PATCHPOINT_COOKIE_NAME=__Host-session
export PATCHPOINT_TLS_REDIRECT=on
export PATCHPOINT_HSTS_MAX_AGE=31536000
export PATCHPOINT_HTTP_BIND="127.0.0.1:$SMOKE_HTTP_PORT"
export PATCHPOINT_HTTPS_BIND="127.0.0.1:$SMOKE_HTTPS_PORT"
export PATCHPOINT_HTTPS_PUBLIC_PORT="$SMOKE_HTTPS_PORT"
export PATCHPOINT_TLS_DIR="$WORK/tls"
export PATCHPOINT_ACME_DIR="$PWD/deploy/proxy/acme"
export PATCHPOINT_API_ENV_FILE="$WORK/api.env"
export PATCHPOINT_BACKEND_SUBNET="$SMOKE_SUBNET"
export PATCHPOINT_PROXY_BACKEND_IP="$SMOKE_PROXY_IP"

docker compose -p "$SMOKE_PROJECT" up -d --wait --wait-timeout 180 >"$WORK/up.log" 2>&1 || die "docker compose up nie powiódł się: $(tail -n 5 "$WORK/up.log" | tr '\n' ' ')"

# Nazwa patchpoint.localhost (curl rozwiązuje *.localhost na pętlę zwrotną) zamiast adresu IP: żądanie z
# nagłówkiem Host będącym adresem IP dostaje punkty anomalii WAF (reguła 920350), a to zmienia wynik
# kontroli i zaśmieca audit log. Certyfikat deweloperski ma SAN patchpoint.localhost.
B="https://patchpoint.localhost:$SMOKE_HTTPS_PORT"
H="http://patchpoint.localhost:$SMOKE_HTTP_PORT"
CURL=(curl -s --noproxy '*' --cacert "$WORK/tls/fullchain.pem")
BODY="$WORK/body"
HDR="$WORK/hdr"
STATUS=000

# req <METODA> <url> [argumenty curl...] — ustawia STATUS, $BODY i $HDR
req() {
  local method="$1" url="$2"
  shift 2
  STATUS=$("${CURL[@]}" -o "$BODY" -D "$HDR" -w '%{http_code}' -X "$method" "$@" "$url" </dev/null) || STATUS=000
  sed -i 's/\r$//' "$HDR"
}

# post_json <url> <json> [argumenty curl...] — ciało żądania idzie przez stdin, nie przez argumenty curla
post_json() {
  local url="$1" json="$2"
  shift 2
  STATUS=$("${CURL[@]}" -o "$BODY" -D "$HDR" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
    --data-binary @- "$@" "$url" <<<"$json") || STATUS=000
  sed -i 's/\r$//' "$HDR"
}

# Nazwy nagłówków mogą mieć dowolną wielkość liter (HTTP/1.1 w nginx zachowuje oryginalną); req i
# post_json usuwają CR z końców linii, a wszystkie kontrole nagłówków są niewrażliwe na wielkość liter.
headers() { cat "$HDR"; }
has_header() { grep -Eiq -- "$1" "$HDR"; }
no_header() { ! grep -Eiq -- "$1" "$HDR"; }
detail_is() { jq -e --arg d "$1" '.detail == $d' "$BODY" >/dev/null 2>&1; }

# cookie_header <plik> <nazwa> <wartość> — nagłówek Cookie w pliku 0600, żeby token nie trafił do argumentów
cookie_header() {
  (umask 077 && printf 'Cookie: %s=%s\n' "$2" "$3" >"$1")
}

WAF_DETAIL="Request blocked by the web application firewall"
RL_DETAIL="Too many requests, try again later"

# 1. UI: nagłówki bezpieczeństwa
req GET "$B/"
index_ok=1
[[ "$STATUS" == "200" ]] || index_ok=0
has_header "^content-security-policy:.*frame-ancestors 'none'" || index_ok=0
has_header "^content-security-policy:.*connect-src 'self'" || index_ok=0
has_header '^strict-transport-security: max-age=31536000$' || index_ok=0
has_header '^x-content-type-options: nosniff$' || index_ok=0
has_header '^x-frame-options: DENY$' || index_ok=0
has_header '^referrer-policy: no-referrer$' || index_ok=0
no_header '^server:' || index_ok=0
if [[ "$index_ok" -eq 1 ]]; then
  ok "UI przez HTTPS: 200, CSP z frame-ancestors, HSTS i nagłówki bezpieczeństwa, bez nagłówka Server"
else
  bad "UI przez HTTPS: status $STATUS albo brak nagłówków bezpieczeństwa (patrz nagłówki: $(head -n 20 "$HDR" | tr '\n' '|'))"
fi

# 2. UI pod jednym originem: adres API podmieniony przy budowie obrazu
index_body="$WORK/index.html"
cp "$BODY" "$index_body"
req GET "$B/app.js"
if [[ "$STATUS" == "200" ]] && grep -qx 'const API_BASE_URL = "";' "$BODY" \
  && grep -qF "connect-src 'self';" "$index_body" && ! grep -qF 'patchpoint.localhost:8000' "$index_body" "$BODY"; then
  ok "UI wywołuje względne /api/ i ma CSP connect-src 'self' w meta"
else
  bad "UI nie ma podmienionego adresu API albo CSP w meta"
fi

# 3. HTTP: przekierowanie na HTTPS, wyjątek ACME
req GET "$H/api/health"
if [[ "$STATUS" == "301" ]] && has_header "^location: https://patchpoint.localhost:$SMOKE_HTTPS_PORT/api/health\$"; then
  ok "HTTP przekierowuje na HTTPS (301)"
else
  bad "HTTP: status $STATUS zamiast 301 na https://patchpoint.localhost:$SMOKE_HTTPS_PORT/api/health"
fi
req GET "$H/.well-known/acme-challenge/smoke-brak"
if [[ "$STATUS" == "404" ]]; then
  ok "wyzwania ACME nie są przekierowywane na HTTPS (404 dla brakującego pliku)"
else
  bad "wyzwanie ACME: status $STATUS zamiast 404"
fi

# 4. API przez proxy
req GET "$B/api/health"
if [[ "$STATUS" == "200" ]] && jq -e '.status == "ok"' "$BODY" >/dev/null 2>&1 \
  && has_header '^cache-control: no-store' && has_header '^strict-transport-security:'; then
  ok "GET /api/health przez proxy: 200, Cache-Control z API i HSTS z proxy"
else
  bad "GET /api/health przez proxy: status $STATUS albo brak nagłówków"
fi

# 5. Demo end-to-end przez proxy (obejmuje PATCH przez WAF i ciasteczko __Host-session)
demo_status=0
CURL_CA_BUNDLE="$WORK/tls/fullchain.pem" API_URL="$B" ./scripts/demo.sh >"$WORK/demo.txt" 2>&1 || demo_status=$?
demo_last=$(tail -n 1 "$WORK/demo.txt")
if [[ "$demo_status" -eq 0 && "$demo_last" == "DEMO ZAKOŃCZONE POWODZENIEM" ]]; then
  ok "demo end-to-end przez proxy (logowanie, zgłoszenia, PATCH, komentarze, wylogowanie)"
else
  bad "demo end-to-end przez proxy: kod $demo_status"
  tail -n 8 "$WORK/demo.txt" | sed 's/^/     /'
fi
echo "     $demo_last"

# 6. Silne hasło przechodzi przez WAF; ciasteczko sesji z prefiksem __Host-
PW_STRONG="Smoke' OR '1'='1' -- <b>$SFX</b>"
SMOKE_USER="smoke.pw.$SFX"
payload=$(printf '%s' "$PW_STRONG" | jq -Rsc --arg u "$SMOKE_USER" '{username: $u, password: ., full_name: "Smoke PW"}')
post_json "$B/api/auth/register" "$payload"
if [[ "$STATUS" == "201" ]]; then
  ok "rejestracja z silnym hasłem (apostrofy, cudzysłowy, znaczniki HTML) przechodzi przez WAF"
else
  bad "rejestracja z silnym hasłem: status $STATUS zamiast 201"
fi
payload=$(printf '%s' "$PW_STRONG" | jq -Rsc --arg u "$SMOKE_USER" '{username: $u, password: .}')
post_json "$B/api/auth/login" "$payload"
TOKEN=""
cookie_ok=0
if [[ "$STATUS" == "200" ]]; then
  cookie_line=$(grep -i -m 1 '^set-cookie: __Host-session=' "$HDR" || true)
  cookie_ok=1
  [[ -n "$cookie_line" ]] || cookie_ok=0
  for attribute in 'HttpOnly' 'Secure' 'Path=/' 'SameSite=strict'; do
    grep -qiF "$attribute" <<<"$cookie_line" || cookie_ok=0
  done
  ! grep -qi 'domain=' <<<"$cookie_line" || cookie_ok=0
  TOKEN=$(sed -e 's/^[^=]*=//' -e 's/;.*$//' <<<"$cookie_line")
fi
if [[ "$cookie_ok" -eq 1 && -n "$TOKEN" ]]; then
  ok "logowanie ustawia __Host-session z HttpOnly, Secure, Path=/, SameSite=Strict i bez Domain"
else
  bad "logowanie: status $STATUS albo ciasteczko __Host-session bez wymaganych atrybutów"
fi
cookie_header "$WORK/cookie.host" "__Host-session" "$TOKEN"
cookie_header "$WORK/cookie.default" "session" "$TOKEN"
req GET "$B/api/auth/me" -H "@$WORK/cookie.host"
host_status="$STATUS"
req GET "$B/api/auth/me" -H "@$WORK/cookie.default"
default_status="$STATUS"
if [[ "$host_status" == "200" && "$default_status" == "401" ]]; then
  ok "sesja działa tylko pod nazwą __Host-session (200), pod nazwą session: 401"
else
  bad "/api/auth/me: z __Host-session $host_status (oczekiwano 200), z session $default_status (oczekiwano 401)"
fi

# 7. Kontrola Origin
req POST "$B/api/auth/logout" -H 'Origin: https://evil.example' -H "@$WORK/cookie.host"
origin_status="$STATUS"
origin_detail=0
detail_is "Origin not allowed" && origin_detail=1
req GET "$B/api/auth/me" -H "@$WORK/cookie.host"
if [[ "$origin_status" == "403" && "$origin_detail" -eq 1 && "$STATUS" == "200" ]]; then
  ok "obcy Origin: 403 \"Origin not allowed\", a sesja pozostaje ważna"
else
  bad "obcy Origin: status $origin_status, następnie /api/auth/me: $STATUS"
fi

# 8. WAF: SQL injection
req GET "$B/api/tickets" -G --data-urlencode "search=1' OR '1'='1" -H "@$WORK/cookie.host"
if [[ "$STATUS" == "403" ]] && detail_is "$WAF_DETAIL"; then
  ok "WAF blokuje SQL injection w parametrze search (403, JSON)"
else
  bad "WAF, SQL injection: status $STATUS zamiast 403 z komunikatem WAF"
fi

# 9. WAF: XSS
payload=$(jq -nc --arg u "smoke.xss.$SFX" --arg p "Smoke-Xss-Password-$SFX" \
  '{username: $u, password: $p, full_name: "<script>alert(1)</script>"}')
post_json "$B/api/auth/register" "$payload"
if [[ "$STATUS" == "403" ]] && detail_is "$WAF_DETAIL"; then
  ok "WAF blokuje XSS w polu full_name (403, JSON)"
else
  bad "WAF, XSS: status $STATUS zamiast 403 z komunikatem WAF"
fi

# 10. Audit log WAF: reguły SQLi i XSS są zapisane, a sekretów w nim nie ma
docker compose -p "$SMOKE_PROJECT" logs proxy >"$WORK/proxy.log" 2>&1 || true
audit_ok=1
grep -Eq '"ruleId": ?"942[0-9]{3}"' "$WORK/proxy.log" || audit_ok=0
grep -Eq '"ruleId": ?"941[0-9]{3}"' "$WORK/proxy.log" || audit_ok=0
if [[ "$audit_ok" -eq 1 ]]; then
  ok "audit log WAF zawiera reguły 942xxx (SQLi) i 941xxx (XSS)"
else
  bad "audit log WAF nie zawiera reguł 942xxx i 941xxx"
fi
leaks=0
for secret in "$PW_STRONG" "$DEMO_PASSWORD" "$TOKEN"; do
  if grep -qF -- "$secret" "$WORK/proxy.log"; then
    leaks=$((leaks + 1))
  fi
done
if [[ "$leaks" -eq 0 ]]; then
  ok "logi proxy nie zawierają haseł ani tokenu sesji"
else
  bad "logi proxy zawierają $leaks sekretów (hasło lub token sesji)"
fi

# 11. client_ip: nagłówek X-Forwarded-For od klienta nie dociera do API
req GET "$B/api/auth/me" -H 'Cookie: __Host-session=smoke-forged' -H 'X-Forwarded-For: 203.0.113.77'
forged_status="$STATUS"
docker compose -p "$SMOKE_PROJECT" logs api >"$WORK/api-stack.log" 2>&1 || true
client_ip=$(python3 - "$WORK/api-stack.log" <<'PY'
import json
import sys

last = None
with open(sys.argv[1], encoding="utf-8", errors="replace") as handle:
    for line in handle:
        if '"event": "session_rejected"' in line and "{" in line:
            last = line
if last is not None:
    try:
        print(json.loads(last[last.index("{") :]).get("client_ip") or "")
    except ValueError:
        pass
PY
)
if [[ "$forged_status" == "401" && -n "$client_ip" && "$client_ip" != "203.0.113.77" && "$client_ip" != "$SMOKE_PROXY_IP" ]]; then
  ok "client_ip w logu API to adres klienta, nie wartość z nagłówka klienta ani adres proxy"
else
  bad "client_ip: status $forged_status, wartość w logu API '${client_ip:-brak}'"
fi

# 12. Izolacja kontenerów i sieci
api_id=$(docker compose -p "$SMOKE_PROJECT" ps -q api)
api_uid=$(docker compose -p "$SMOKE_PROJECT" exec -T api id -u 2>/dev/null | tr -d '\r' || true)
proxy_uid=$(docker compose -p "$SMOKE_PROJECT" exec -T proxy id -u 2>/dev/null | tr -d '\r' || true)
if [[ "$api_uid" == "10001" && "$proxy_uid" == "101" ]]; then
  ok "procesy bez uprawnień roota: API 10001, proxy 101"
else
  bad "UID procesów: API '$api_uid' (oczekiwano 10001), proxy '$proxy_uid' (oczekiwano 101)"
fi
if [[ -n "$api_id" ]] \
  && [[ "$(docker inspect -f '{{.HostConfig.ReadonlyRootfs}}' "$api_id")" == "true" ]] \
  && docker inspect -f '{{json .HostConfig.CapDrop}}' "$api_id" | grep -qF 'ALL' \
  && docker inspect -f '{{json .HostConfig.SecurityOpt}}' "$api_id" | grep -qF 'no-new-privileges:true'; then
  ok "kontener API: system plików tylko do odczytu, cap_drop ALL, no-new-privileges"
else
  bad "kontener API bez read-only, cap_drop ALL albo no-new-privileges"
fi
# Dla portu bez publikacji compose wypisuje ":0" albo nic (zależnie od wersji).
published=$(docker compose -p "$SMOKE_PROJECT" port api 8000 2>/dev/null) || published=""
if [[ -z "$published" || "$published" == ":0" ]]; then
  ok "API nie ma opublikowanego portu"
else
  bad "API ma opublikowany port: $published"
fi
if docker compose -p "$SMOKE_PROJECT" exec -T api python -c "import socket; socket.create_connection(('1.1.1.1', 443), timeout=3)" >/dev/null 2>&1; then
  bad "API ma wyjście do Internetu (połączenie z 1.1.1.1:443 się powiodło)"
else
  ok "API nie ma wyjścia do Internetu (sieć backend: internal)"
fi

# 13. Limit żądań dla logowania (zawsze ostatnia kontrola: wyczerpuje limit)
limited=0
rl_problems=0
rl_statuses=""
for i in $(seq 1 12); do
  payload=$(jq -nc --arg u "smoke.rl.$i.$SFX" '{username: $u, password: "wrong-password-123456"}')
  post_json "$B/api/auth/login" "$payload"
  rl_statuses="$rl_statuses $STATUS"
  case "$STATUS" in
    429)
      limited=$((limited + 1))
      detail_is "$RL_DETAIL" || rl_problems=$((rl_problems + 1))
      ;;
    401) ;;
    *) rl_problems=$((rl_problems + 1)) ;;
  esac
done
if [[ "$limited" -ge 1 && "$rl_problems" -eq 0 ]]; then
  ok "limit żądań logowania: $limited z 12 odpowiedzi to 429 z JSON, pozostałe 401 (bez 5xx)"
else
  bad "limit żądań logowania: statusy$rl_statuses (429 co najmniej raz, reszta 401, komunikat JSON)"
fi

echo
if [[ "$FAILURES" -gt 0 ]]; then
  echo "STACK SMOKE: $FAILURES błędów"
  exit 1
fi
echo "STACK SMOKE ZAKOŃCZONY POWODZENIEM"
