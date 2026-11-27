# Test Report: patchpoint-phase-3-ops

## Summary
- Total: 16 | Pass: 16 | Fail: 0 | Skip: 0 | Need info: 0
- Plan: docs/testing/plans/2026-11-27-patchpoint-phase-3-ops-test-plan.md
- Plan provenance: hand-written; executed by hand (curl, openssl, docker compose), not by the `/qa:run` engine, so there is no loop-state file and no `responses/` directory
- Date: 2026-11-27
- Images: built locally from the working tree (`make images`); compose project `patchpoint-qa3`, HTTP on 127.0.0.1:18080 and HTTPS on 127.0.0.1:18443 (8080 and 8443 were taken on the host); public origins set to those two ports
- Accounts: registered 1 (`qa3.<random>`) in the throw-away `patchpoint-qa3` volume; the stack was removed after the run

## Issues Found

None.

## Detailed Results

### Pass: BE-01: UI over HTTPS carries the security headers and no Server header
`200`; CSP with `frame-ancestors 'none'` and `connect-src 'self'`, `Strict-Transport-Security: max-age=0`, `nosniff`, `DENY`, `no-referrer`; no `Server` header.
### Pass: BE-02: The UI calls the API with relative paths on one origin
`app.js` `200`, `const API_BASE_URL = "";`, no `patchpoint.localhost:8000` in `index.html` or `app.js`.
### Pass: BE-03: The development certificate is a server certificate only and is verified through the trust file
SAN `DNS:patchpoint.localhost`, `CA:FALSE`, serverAuth; TLS 1.3, verify code 0 with `--cacert`; `curl` without it exits 60.
### Pass: BE-04: Local HTTP serves the application; ACME paths are not redirected
`/api/health` `200` without redirect; missing ACME file `404`.
### Pass: BE-05: API documentation is not reachable through the proxy
`/docs`, `/redoc`, `/openapi.json` → `404`.
### Pass: BE-06: A strong password with quotes and HTML passes the WAF
`201`.
### Pass: BE-07: Login sets the session cookie with the required attributes
Login `200`; cookie `HttpOnly`, `Secure`, `Path=/`, `SameSite=Strict`, no `Domain`; `/api/auth/me` `200`.
### Pass: BE-08: A foreign Origin is refused and does not end the session
Logout with `Origin: https://evil.example` → `403` `Origin not allowed`; `/api/auth/me` afterwards `200`.
### Pass: BE-09: The WAF blocks SQL injection in a query parameter
`403` `{"detail":"Request blocked by the proxy"}`.
### Pass: BE-10: The WAF blocks script injection in a body field
`403` `{"detail":"Request blocked by the proxy"}`.
### Pass: BE-11: nginx's own 403 uses the same neutral message
`/metrics/nginx` → `403` `{"detail":"Request blocked by the proxy"}`.
### Pass: BE-12: The WAF audit log records the attacks and none of the secrets
Rule ids 942xxx and 941xxx present; the BE-06 password and the BE-07 token appear in the proxy log 0 times.
### Pass: BE-13: A client-supplied X-Forwarded-For does not reach the API log
`401`; `client_ip` in the API log `172.20.0.1`, which is neither `203.0.113.77` nor the proxy's backend address `10.252.0.10`.
### Pass: BE-14: Container isolation
UID API 10001 and proxy 101; API `ReadonlyRootfs=true`, `CapDrop=["ALL"]`, `SecurityOpt=["no-new-privileges:true"]`; `docker compose port api 8000` → `:0`; connect to 1.1.1.1:443 from the API container failed.
### Pass: BE-15: Login is rate-limited per client IP
12 attempts: `401 401 401 401 429 429 429 429 429 429 429 429` (burst 5 allowed, then `429` with the JSON message).
### Pass: BE-16: The Ansible bootstrap certificate is a server certificate with a SAN
The `argv` read from the task YAML and run for `helpdesk.example.com`: SAN `DNS:helpdesk.example.com`, `basicConstraints` critical `CA:FALSE`, `extendedKeyUsage` `TLS Web Server Authentication`.

## Not covered

- The `__Host-session` cookie name, HSTS `max-age=31536000` and the HTTP→HTTPS `301`: production values of `PATCHPOINT_COOKIE_NAME`, `PATCHPOINT_HSTS_MAX_AGE` and `PATCHPOINT_TLS_REDIRECT`; `scripts/stack_smoke.sh` runs the stack with them ([evidence](../../faza-3-ops/dowody/smoke-stosu.txt)).
- The Ansible playbook against a real VPS (nftables, systemd drop-in, Let's Encrypt, GHCR deploy): needs a server; only `ansible-lint` and `--syntax-check` ran.
- FE scenarios: the UI was not changed in Phase 3.
