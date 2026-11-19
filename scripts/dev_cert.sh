#!/usr/bin/env bash
# Certyfikat deweloperski (self-signed, 30 dni) dla https://patchpoint.localhost i https://127.0.0.1;
# tylko lokalnie i w CI. Użycie: scripts/dev_cert.sh <katalog>  (make dev-cert: deploy/proxy/dev-tls)
set -euo pipefail

dir="${1:?Użycie: scripts/dev_cert.sh <katalog>}"
if [[ -s "$dir/fullchain.pem" && -s "$dir/privkey.pem" ]] \
  && openssl x509 -checkend 86400 -noout -in "$dir/fullchain.pem" >/dev/null; then
  echo "Certyfikat deweloperski w $dir jest ważny."
  exit 0
fi
mkdir -p "$dir"
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -noenc -days 30 \
  -subj "/CN=patchpoint.localhost" \
  -addext "subjectAltName=DNS:patchpoint.localhost,IP:127.0.0.1" \
  -keyout "$dir/privkey.pem" -out "$dir/fullchain.pem" 2>/dev/null
# Proxy działa jako UID 101, a pliki są montowane z hosta, więc klucz musi być czytelny dla wszystkich.
# Dopuszczalne wyłącznie dla tego jednorazowego klucza deweloperskiego.
chmod 0755 "$dir"
chmod 0644 "$dir/fullchain.pem" "$dir/privkey.pem"
echo "Utworzono certyfikat deweloperski: $dir/fullchain.pem"
