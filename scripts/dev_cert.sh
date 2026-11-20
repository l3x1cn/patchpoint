#!/usr/bin/env bash
# Certyfikat deweloperski (self-signed, 30 dni) dla https://patchpoint.localhost i https://127.0.0.1;
# tylko lokalnie i w CI. Użycie: scripts/dev_cert.sh <katalog>  (make dev-cert: deploy/proxy/dev-tls)
set -euo pipefail

dir="${1:?Użycie: scripts/dev_cert.sh <katalog>}"
# Istniejący certyfikat jest używany ponownie tylko wtedy, gdy ma basicConstraints CA:FALSE; starsze
# certyfikaty (z CA:TRUE, które openssl dodaje domyślnie do self-signed) są generowane od nowa.
if [[ -s "$dir/fullchain.pem" && -s "$dir/privkey.pem" ]] \
  && openssl x509 -checkend 86400 -noout -in "$dir/fullchain.pem" >/dev/null \
  && openssl x509 -noout -ext basicConstraints -in "$dir/fullchain.pem" | grep -q 'CA:FALSE'; then
  echo "Certyfikat deweloperski w $dir jest ważny."
  exit 0
fi
mkdir -p "$dir"
# basicConstraints CA:FALSE i extendedKeyUsage serverAuth: certyfikat jest zaufany jako --cacert, więc nie
# może działać jako urząd certyfikacji (bez tego openssl wystawia self-signed z CA:TRUE) ani służyć
# do niczego poza uwierzytelnieniem serwera TLS.
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -noenc -days 30 \
  -subj "/CN=patchpoint.localhost" \
  -addext "subjectAltName=DNS:patchpoint.localhost,IP:127.0.0.1" \
  -addext "basicConstraints=critical,CA:FALSE" \
  -addext "extendedKeyUsage=serverAuth" \
  -keyout "$dir/privkey.pem" -out "$dir/fullchain.pem" 2>/dev/null
# Proxy działa jako UID 101, a pliki są montowane z hosta, więc klucz musi być czytelny dla wszystkich.
# Kompromis (zapisana decyzja): każdy lokalny użytkownik hosta może odczytać ten klucz, a certyfikat jest
# self-signed, więc kto go przejmie, może podszyć się pod serwer tylko u klientów, którzy mu zaufali
# (--cacert). Dopuszczalne wyłącznie dla tego jednorazowego klucza deweloperskiego (30 dni), nigdy dla
# produkcji.
chmod 0755 "$dir"
chmod 0644 "$dir/fullchain.pem" "$dir/privkey.pem"
echo "Utworzono certyfikat deweloperski: $dir/fullchain.pem"
