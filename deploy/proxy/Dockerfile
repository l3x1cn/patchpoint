# Obraz reverse proxy PatchPoint (Faza 3): nginx bez uprawnień roota (użytkownik nginx, UID 101)
# z ModSecurity 3 i OWASP CRS 4.30 z obrazu owasp/modsecurity-crs (Alpine), przypiętego po digeście.
# Jeden origin: statyczny UI oraz /api/ przekazywane do kontenera API; TLS, HSTS, WAF, limit żądań.
# Kontekst to katalog główny repozytorium; plik kontekstu: deploy/proxy/Dockerfile.dockerignore.
#   make images  (docker build -f deploy/proxy/Dockerfile -t patchpoint-proxy:local .)

FROM owasp/modsecurity-crs:4.30.0-nginx-alpine-202611160811@sha256:27eba34c27e432ef0c8939f3695b5483952247ae298fee881e02ca96fb44563a AS ui
USER root
WORKDIR /ui
# Pliki w repozytorium mogą mieć tryb 0600; użytkownik nginx (UID 101) musi móc je czytać.
COPY --chmod=u=rwX,go=rX frontend/index.html frontend/app.js frontend/styles.css ./
# UI i API pod jednym originem: klient woła względne /api/..., a CSP z <meta> dopuszcza tylko 'self'.
# grep przerywa budowę, gdy źródłowe linie się zmienią i podmiana przestanie działać.
RUN sed -i 's|^const API_BASE_URL = "http://patchpoint.localhost:8000";$|const API_BASE_URL = "";|' app.js \
    && grep -qx 'const API_BASE_URL = "";' app.js \
    && sed -i "s|connect-src http://patchpoint.localhost:8000;|connect-src 'self';|" index.html \
    && grep -qF "connect-src 'self';" index.html \
    && ! grep -qF 'patchpoint.localhost:8000' app.js index.html

FROM owasp/modsecurity-crs:4.30.0-nginx-alpine-202611160811@sha256:27eba34c27e432ef0c8939f3695b5483952247ae298fee881e02ca96fb44563a
# Wartości domyślne (produkcyjne); compose.yaml nadpisuje te zależne od środowiska.
# SSL_OCSP_STAPLING=off: certyfikat deweloperski nie ma adresu OCSP; dla Let's Encrypt ustawienie jest
# bezpieczne niezależnie od tego, czy certyfikat ma adres OCSP.
# MODSEC_AUDIT_LOG_PARTS=AFHZ: bez części B, I i J, czyli bez nagłówków i ciała żądań (ciasteczko, hasło).
ENV BACKEND=http://api:8000 \
    SERVER_NAME=patchpoint.localhost \
    PORT=8080 \
    SSL_PORT=8443 \
    SSL_CERT_FILE=/etc/nginx/tls/fullchain.pem \
    SSL_CERT_KEY_FILE=/etc/nginx/tls/privkey.pem \
    SSL_OCSP_STAPLING=off \
    NGINX_ALWAYS_TLS_REDIRECT=on \
    PATCHPOINT_HSTS_MAX_AGE=31536000 \
    PATCHPOINT_AUTH_RATE=10r/m \
    PATCHPOINT_AUTH_BURST=5 \
    BLOCKING_PARANOIA=1 \
    ANOMALY_INBOUND=5 \
    ANOMALY_OUTBOUND=4 \
    ALLOWED_METHODS="GET HEAD POST PATCH OPTIONS" \
    MODSEC_RULE_ENGINE=on \
    MODSEC_AUDIT_LOG_FORMAT=JSON \
    MODSEC_AUDIT_LOG_PARTS=AFHZ
COPY --from=ui --chmod=u=rwX,go=rX /ui/ /usr/share/nginx/html/
COPY --chmod=u=rwX,go=rX deploy/proxy/templates/ /etc/nginx/templates/
COPY --chmod=u=rw,go=r deploy/proxy/modsecurity/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf /opt/owasp-crs/rules/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf
USER nginx
EXPOSE 8080 8443
# Wbudowany HEALTHCHECK obrazu woła curl bez -f (zdrowy przy każdym statusie HTTP); ten sprawdza status.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --start-interval=2s --retries=3 \
    CMD ["curl", "-fsk", "-o", "/dev/null", "https://localhost:8443/healthz"]
