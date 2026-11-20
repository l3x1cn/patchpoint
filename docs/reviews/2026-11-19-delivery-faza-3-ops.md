# Code Review: delivery/faza-3-ops

Review scope: changes since 06f48cf (67 files)

Review request: Changes on branch delivery/faza-3-ops in main..HEAD, delivered from docs/plans/2026-11-18-faza-3-ops.md. Review only these changes.

## Summary

Phase 3 (OPS) adds two hardened container images (API on `python:3.14.10-slim`, UID 10001; reverse proxy on `owasp/modsecurity-crs` with TLS, HSTS, CRS WAF and a per-IP limit), a compose stack with the API on an `internal` network, scan gates (Semgrep, Trivy) that run from digest-pinned images, a GitHub Actions pipeline (scans, then build, image gate, stack smoke, publish), an Ansible playbook for a VPS (nftables, sshd, Docker, certbot), a configurable session cookie name for the `__Host-` prefix, and the Ops report with its evidence. The delivery checks agree: ruff (with `S`), mypy strict and 145 tests pass at 98% coverage, the stack smoke test passes with 22 × `[NAPRAWIONE]` in the API container, `make semgrep`, `make trivy-fs` and `make trivy-images` exit 0, `make ansible-lint` passes in the production profile, and CI run 44520467614 is green. QA was not run (port 8080 on the development machine is held by another project, the user chose to skip it).

The review found no CRITICAL issue. One HIGH finding is a documentation claim that is false and weakens credential rotation (DOC-001). Seventeen issue blocks remain: one HIGH, two MEDIUM (host patching of the Docker runtime, the network-flow claim in the report) and fourteen LOW, one of which is a composite of two others (COMP-001). Two findings were downgraded by the challenger and one duplicate was merged.

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 2 |
| LOW | 14 |

Scans that ran: ruff (with `S`), mypy strict, shellcheck 0.11.0 (`scan.sh`, `stack_smoke.sh`, `dev_cert.sh`: 0 findings), actionlint 1.7.12 (`ci.yml`: 0 findings), Semgrep 1.185.0 with the repository gate (275 rules) and a wider set (355 rules), Bandit, pip-audit, trufflehog and gitleaks over the 12 commits (0 secrets), Trivy fs and image scans, and live checks against a throwaway compose stack (WAF, rate limit, redirect, audit log, nginx CVE mitigations).

## Security

### [MEDIUM] SEC-001: Docker Engine, containerd and runc never get security updates
**Status:** ✅ Fixed (2026-11-19)

**ID:** SEC-001
**Location:** `deploy/ansible/roles/docker/tasks/main.yml:20`
**Category:** Security
**OWASP:** A03:2025
**CWE:** CWE-1395
**Effort:** easy

**Problem:**
The `docker` role installs `docker_packages` from download.docker.com with `state: present`, so a repeated run never upgrades them. The `base` role enables unattended-upgrades (`roles/base/templates/20auto-upgrades.j2:3`), but its stock origin lists cover only the distribution archives and their security pockets, not the Docker repository (origin `Docker`, label `Docker CE`; the origin names are an inference from `apt-cache policy`, not observed on a target host). runc, containerd and dockerd are the boundary between the internet-facing proxy and root on the host, and they stay at the install-day version. Neither section 9 nor section 13 of `docs/faza-3-ops/README.md` mentions this, and section 9 presents unattended-upgrades as the update mechanism of the host.

**Impact:**
Code execution inside the proxy container (writable filesystem, Internet egress, the accepted nginx CVEs until 2026-12-19) plus a container-escape CVE published after provisioning gives root on the VPS, with the GHCR token in `/root/.docker/config.json`, the TLS key and the SQLite database.

**Remediation:**

```yaml
# Before: docker packages are installed once and never updated
# After: allow the Docker origin in unattended-upgrades (live-restore keeps containers running)
- name: Włącz automatyczne aktualizacje pakietów Dockera
  ansible.builtin.copy:
    dest: /etc/apt/apt.conf.d/52patchpoint-docker
    owner: root
    group: root
    mode: "0644"
    content: |
      Unattended-Upgrade::Origins-Pattern:: "origin=Docker,label=Docker CE";
```

Alternatively use `state: latest` with a documented patch schedule. Add the item to section 13 of the Ops report next to the `DOCKER-USER` item.

---

### [LOW] SEC-002: Deployment pulls mutable image tags instead of digests
**Status:** ⚠️ Partially Fixed (2026-11-19)

**ID:** SEC-002
**Location:** `deploy/ansible/roles/patchpoint/templates/env.j2:3`
**Category:** Security
**OWASP:** A08:2025
**CWE:** CWE-494
**Effort:** medium

**Problem:**
`env.j2:3-4` deploys `ghcr.io/l3x1cn/patchpoint/{api,proxy}:sha-<7>` and `roles/patchpoint/tasks/main.yml:95` pulls with `pull: always`. GHCR tags can be overwritten: a re-run of the workflow for the same commit rebuilds the image (the rebuild differs because `apt-get upgrade` runs at build time) and `publish` (`.github/workflows/ci.yml:184-185`) pushes it over the same tag, and anything holding `packages: write` can overwrite a tag. Section 8 says the scanned image is the published image; that is true at push time but is not checked at deploy time. A related documentation gap: the rollback procedure in section 9 (`docs/faza-3-ops/README.md:239-240`, "poprzedni tag") assumes a tag always points to one image.

**Impact:**
A rollback to `sha-<previous>` deploys whatever the tag points to now, which may be a rebuilt image or a substitute pushed with a compromised credential. The server does not tie the deployed image to the build that passed the gates.

**Remediation:**

```yaml
# Before
PATCHPOINT_API_IMAGE={{ patchpoint_image_repo }}/api:{{ patchpoint_image_tag }}
# After: record the pushed digests in `publish` and deploy by digest
PATCHPOINT_API_IMAGE={{ patchpoint_image_repo }}/api@{{ patchpoint_api_digest }}  # assert: match('^sha256:[0-9a-f]{64}$')
```

Optionally sign keyless with cosign (`id-token: write` on `publish`) and verify before `docker_compose_v2`. Record the tag-overwrite limitation in section 13.

---

### [LOW] SEC-003: Ansible tooling resolves unpinned transitive dependencies from PyPI on every run
**Status:** ✅ Fixed (2026-11-19)

**ID:** SEC-003
**Location:** `Makefile:74`
**Category:** Security
**OWASP:** A03:2025
**CWE:** CWE-829
**Effort:** medium

**Problem:**
`make ansible-lint` (`Makefile:14` and `74-76`) runs `uvx --from ansible-lint==26.11.0 --with ansible-core==2.19.15`. Only those two packages are pinned; every other dependency is resolved fresh from PyPI with no lock, no hashes and no Dependabot cooldown. This runs in the CI `ansible` job and on administrator workstations that hold the Vault password and the SSH keys. The backend, by contrast, uses a locked `uv.lock`. `docs/faza-3-ops/README.md:33` says tools are pinned by digest or full SHA, which does not hold for this toolchain; the uv version in CI (`UV_VERSION`, `.github/workflows/ci.yml:36`) is also missing from the manual-bump list (see DOC-005).

**Impact:**
A malicious release of a transitive dependency (as in the CVE-2026-33634 incident) runs on the next `make ansible-lint` and can read `~/.ssh` and capture the Vault password.

**Remediation:**

```make
# Before
ansible-lint:
	cd $(ANSIBLE_DIR) && uvx --python $(ANSIBLE_PYTHON) --from ansible-lint==$(ANSIBLE_LINT_VERSION) --with ansible-core==$(ANSIBLE_CORE_VERSION) ansible-lint
# After: a small locked uv project covered by Dependabot's uv ecosystem
# deploy/ansible/tools/pyproject.toml: dependencies = ["ansible-core==2.19.15", "ansible-lint==26.11.0"]
ansible-lint:
	cd $(ANSIBLE_DIR) && uv run --locked --project tools ansible-lint
```

---

### [LOW] SEC-004: Smoke script puts the demo password and the session token on the command line of grep
**Status:** ✅ Fixed (2026-11-19)

**ID:** SEC-004
**Part-of:** COMP-001
**Location:** `scripts/stack_smoke.sh:132`
**Category:** Security
**OWASP:** A02:2025
**CWE:** CWE-214
**Effort:** trivial

**Problem:**
`grep -cF "$DEMO_PASSWORD"` (line 132) and `grep -qF -- "$secret"` (line 355, covering `$PW_STRONG`, `$DEMO_PASSWORD` and `$TOKEN`) pass secrets as process arguments, which other local users can read in `/proc/<pid>/cmdline`. The script header (line 7) and `docs/faza-3-ops/README.md:181` both say the smoke test never puts passwords or tokens in process arguments, and the shared rules of the plan say the same.

**Impact:**
On a shared development host or a self-hosted runner another local user polls `/proc` during the check and obtains the demo password (valid for every seeded account, including agents) and a live session token for the stack on 127.0.0.1 while it runs. The values are random and short-lived, so the practical risk is small; the written guarantee is false.

**Remediation:**

```bash
# Before
grep -cF "$DEMO_PASSWORD" "$WORK/api.log"
# After (printf is a builtin; the pattern reaches grep through a file descriptor)
grep -cFf <(printf '%s\n' "$DEMO_PASSWORD") "$WORK/api.log"
```

---

### [LOW] SEC-005: Development TLS certificate can act as a CA and its key is world-readable
**Status:** ✅ Fixed (2026-11-19)

**ID:** SEC-005
**Location:** `scripts/dev_cert.sh:13`
**Category:** Security
**OWASP:** A04:2025
**CWE:** CWE-732
**Effort:** trivial

**Problem:**
`openssl req -x509` without extension overrides produces `basicConstraints: critical, CA:TRUE` (checked on `deploy/proxy/dev-tls/fullchain.pem`) and no extended key usage. Lines 20-21 then make the key 0644 in a 0755 directory. The world-readable key is a recorded decision; the CA flag is not.

**Impact:**
If a developer imports the certificate into a trust store to silence browser warnings, anyone who can read the key can sign certificates for any domain and intercept that developer's HTTPS traffic.

**Remediation:**

```bash
# Before
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -noenc -days 30 ...
# After: a leaf certificate that cannot sign others (curl --cacert still accepts it as a trust anchor, tested)
openssl req -x509 ... -addext "basicConstraints=critical,CA:FALSE" -addext "extendedKeyUsage=serverAuth"
```

---

## Performance

No performance findings.

## Maintainability

### [LOW] MAINT-001: The letsencrypt role duplicates paths and the proxy UID owned by the patchpoint role
**Status:** ✅ Fixed (2026-11-19)

**ID:** MAINT-001
**Location:** `deploy/ansible/roles/letsencrypt/defaults/main.yml:4-7`
**Category:** Maintainability
**Effort:** trivial

**Problem:**
`patchpoint_dir` and `patchpoint_proxy_uid` are role defaults (`roles/patchpoint/defaults/main.yml:2,14`), so they are meant to be overridable. The `letsencrypt` role hard-codes the same values (`/opt/patchpoint/acme`, `/opt/patchpoint/tls`, `/opt/patchpoint`, UID 101; also used in `roles/letsencrypt/templates/patchpoint-cert-deploy.sh.j2:7,9,12`). `group_vars/patchpoint/vars.yml:6-7` already passes domain and email but not these four values. The defaults came verbatim from the plan; the challenger downgraded the finding from MEDIUM to LOW because `patchpoint_dir` is not an advertised knob and the documentation hard-codes `/opt/patchpoint` in more than ten places.

**Impact:**
If `patchpoint_dir` or the proxy UID is overridden, certbot writes challenges to a directory the proxy does not mount, or the renewal hook installs a key the proxy cannot read; the latter would only show at the first renewal, about 60 days after issuance. There are four places to keep in sync by hand.

**Remediation:**

```yaml
# Before (group_vars/patchpoint/vars.yml)
letsencrypt_domain: "{{ patchpoint_domain }}"
letsencrypt_email: "{{ patchpoint_acme_email }}"
# After
letsencrypt_domain: "{{ patchpoint_domain }}"
letsencrypt_email: "{{ patchpoint_acme_email }}"
letsencrypt_webroot: "{{ patchpoint_dir }}/acme"
letsencrypt_tls_dir: "{{ patchpoint_dir }}/tls"
letsencrypt_compose_dir: "{{ patchpoint_dir }}"
letsencrypt_proxy_uid: "{{ patchpoint_proxy_uid }}"
```

---

### [LOW] MAINT-002: Every 403 generated by nginx is reported as a WAF block
**Status:** ✅ Fixed (2026-11-19)

**ID:** MAINT-002
**Location:** `deploy/proxy/templates/includes/patchpoint-app.conf.template:8`
**Category:** Maintainability
**Effort:** easy

**Problem:**
`error_page 403 = @patchpoint_waf_blocked` applies to the whole server (named location at lines 35-39), so it also catches 403s unrelated to ModSecurity. The IP allow/deny of `/metrics/nginx` comes from the base image's `includes/location_common.conf`; checked against `patchpoint-proxy:local`, `GET /metrics/nginx` returns 403 with `{"detail":"Request blocked by the web application firewall"}`.

**Impact:**
Operators and clients look for a ModSecurity audit-log entry that does not exist, which slows down triage.

**Remediation:**

```nginx
# Before
return 403 '{"detail":"Request blocked by the web application firewall"}';
# After (and update WAF_DETAIL in scripts/stack_smoke.sh and section 6 of the Ops report)
return 403 '{"detail":"Request blocked by the proxy"}';
```

Alternatively keep the text and document that `/metrics/nginx` denials also produce it.

---

### [LOW] MAINT-003: An empty TOKEN makes the log-leak check report a false leak
**Status:** ✅ Fixed (2026-11-19)

**ID:** MAINT-003
**Part-of:** COMP-001
**Location:** `scripts/stack_smoke.sh:354`
**Category:** Maintainability
**Effort:** trivial

**Problem:**
When the login check fails, `TOKEN` stays `""` (set at `:284` and `:294`). `grep -qF -- "" file` matches every non-empty file, so check 10 also reports "logi proxy zawierają 1 sekretów" when nothing leaked.

**Impact:**
One real failure looks like a secret leak as well, which sends the person debugging it in the wrong direction.

**Remediation:**

```bash
for secret in "$PW_STRONG" "$DEMO_PASSWORD" "$TOKEN"; do
  [[ -n "$secret" ]] || continue
  ...
```

---

### [LOW] MAINT-004: The scan header and the README say trivy-fs fails on any HIGH or CRITICAL, but the code ignores unfixed vulnerabilities
**Status:** ✅ Fixed (2026-11-19)

**ID:** MAINT-004
**Location:** `scripts/scan.sh:5-6`
**Category:** Maintainability
**Effort:** trivial

**Problem:**
The `fs` gate runs with `--ignore-unfixed` (`scripts/scan.sh:88`), but the header of `scan.sh` and the make table in `README.md:198` say "kod 1 przy HIGH lub CRITICAL" without the qualifier "z dostępną poprawką" that the `image` mode and `docs/faza-3-ops/README.md:202` state.

**Impact:**
Readers expect an unfixed HIGH CVE in `uv.lock` to block CI; it does not.

**Remediation:**
Add "z dostępną poprawką" to `scripts/scan.sh:6` and to `README.md:198`.

---

### [LOW] MAINT-005: `.trivyignore` points to the version table in the plan instead of the Ops report
**Status:** ✅ Fixed (2026-11-19)

**ID:** MAINT-005
**Location:** `.trivyignore:9`
**Category:** Maintainability
**Effort:** trivial

**Problem:**
The retirement procedure says "podbić obraz (tabela wersji w planie Fazy 3)". `.github/dependabot.yml:4` and the Ops report (section 3, "Przypięte wersje") name the table in `docs/faza-3-ops/README.md` as the reference; the plan is a historical document. The block holds the six nginx exceptions that expire on 2026-12-19, so whoever handles the expiry follows this pointer.

**Impact:**
The new image digest is bumped in a table nobody maintains.

**Remediation:**
Change the text to `(tabela „Przypięte wersje” w docs/faza-3-ops/README.md)`.

---

## Documentation

### [HIGH] DOC-001: The demo password rotation procedure relies on mechanisms the API does not have
**Status:** ✅ Fixed (2026-11-19)
**Verification:** hard — grep „zmienia się w aplikacji” in docs and README.md → 0 matches; grep „down -v” in docs/faza-3-ops/README.md → 2 matches; relative-link check → 0 missing

**ID:** DOC-001
**Location:** `docs/faza-3-ops/README.md:175`
**Category:** Documentation
**Drift-class:** decision
**Fix-policy:** needs-decision

**Problem:**
The "Rotacja" cell for the demo password says „zmiana w Vault i ponowne wdrożenie; hasła zapisane w bazie zmienia się w aplikacji”. Neither half works. A redeploy rewrites `secrets/api.env`, but `seed_demo_data` returns as soon as the `users` table is not empty (`backend/app/database.py:205-207`; `README.md:142` says the same: „Dane powstają tylko na pustej bazie”), and the repository has no password-change endpoint and no `UPDATE users` (routers: health, auth with register, login, logout and me, tickets). The challenger confirmed both points.

**Impact:**
After a demo password leaks, an operator who follows the table believes it was rotated while the old password keeps working for every demo account, including the agent accounts that can only be created through the seed.

**Remediation:**
Describe what actually happens: a new Vault password only takes effect on an empty database, `docker compose down -v` deletes all data, and in production `patchpoint_seed_demo_data` stays `false`. Add "no password change in the application" to section 13. Adding a password-change path instead is a code decision.

---

### [MEDIUM] DOC-002: The flow table says everything else is dropped, but the host firewall filters only incoming traffic
**Status:** ✅ Fixed (2026-11-19)
**Verification:** hard — grep „odrzucane (polityka” in README.md, docs/raport-devsecops.md and docs/faza-3-ops → 0 matches; grep „nie jest filtrowany|nie filtruje ruchu wychodzącego” in docs/faza-3-ops/README.md → 3 lines (94, 95, 315)

**ID:** DOC-002
**Location:** `docs/faza-3-ops/README.md:94`
**Category:** Documentation
**Drift-class:** decision
**Fix-policy:** needs-decision

**Problem:**
The last row of the flow table says „wszystko inne — odrzucane (polityka `drop` nftables, sieć `internal`)” and line 93 limits host egress to 443. The only chain in `deploy/ansible/roles/base/templates/nftables.conf.j2:9-10` is `input`: outgoing traffic from the host on any port is not filtered, and the proxy reaches the Internet through `edge` (section 13, `:301`, admits this). The enumerated egress is also incomplete (DNS, NTP, apt over port 80 are missing). The row's wording came from the plan, but the plan never decided to filter egress. Section 4 is the graded logical network architecture. The cross-verifier calibrated this to HIGH because it misstates the control that would limit the blast radius of SEC-001; the challenger kept MEDIUM, which is used here.

**Impact:**
A reader assumes egress filtering exists when it does not.

**Remediation:**
Narrow the row to incoming traffic to the host and to the `backend` network, state that outgoing traffic from the host and from `edge` is not filtered, and add this to section 13 next to the `DOCKER-USER` item. Alternatively add an `output` chain to `nftables.conf.j2` (a code decision).

---

### [LOW] DOC-003: The local image scan evidence is credited with six `.trivyignore` exceptions, but it ran with five
**Status:** ✅ Fixed (2026-11-19)
**Verification:** hard — grep „5 wyjątk” → docs/faza-3-ops/README.md:303 and docs/faza-3-ops/dowody/README.md:12; grep „6 wyjątk” in both files → 0 matches; relative-link check → 0 missing

**ID:** DOC-003
**Location:** `docs/faza-3-ops/README.md:290`
**Category:** Documentation
**Drift-class:** decision
**Fix-policy:** needs-decision

**Problem:**
`docs/faza-3-ops/README.md:290` and `docs/faza-3-ops/dowody/README.md:12` tie `trivy-obrazy.txt` to "6 wyjątków `.trivyignore`". The file was produced at `fe314cb`, when `.trivyignore` had five entries; the sixth (CVE-2026-118899) was added in `26d93eb` after the CI gate reported it. `dowody/triaz-skanow.md:37` says so itself. The challenger downgraded the finding from MEDIUM to LOW: the local output is identical with five or six entries, and the six-exception gate is evidenced by CI run 44520467614.

**Impact:**
The evidence describes a configuration it was not produced with.

**Remediation:**
Restore "5 wyjątków" with a note that the sixth gate is covered by CI (`dowody/ci.md`), or regenerate `trivy-obrazy.txt` on the current tree. Also correct the related claim at `dowody/README.md:23` ("zadanie 9 dodaje tylko dokumentację"), since `26d93eb` changed `.trivyignore`.

---

### [LOW] DOC-004: The rationale for the `request-host-used` exception cites smoke and the local stack, which no longer redirect by IP address
**Status:** ✅ Fixed (2026-11-19)
**Verification:** hard — grep „nosemgrep” in deploy/proxy/templates/conf.d/default.conf.template → 0; grep „return 301” → fixed server name; make semgrep → 0 findings; make stack-smoke → STACK SMOKE ZAKOŃCZONY POWODZENIEM; make trivy-images → exit 0

**ID:** DOC-004
**Location:** `docs/faza-3-ops/dowody/triaz-skanow.md:22`
**Category:** Documentation
**Drift-class:** decision
**Fix-policy:** needs-decision

**Problem:**
The justification reads „stała nazwa zepsułaby wejście przez adres IP (smoke, lokalny stos)”, which was true for the plan's smoke (127.0.0.1). The implemented smoke connects by name (`scripts/stack_smoke.sh:170-171`) and the local stack does no redirect (`compose.yaml:62`, `PATCHPOINT_TLS_REDIRECT=off`). The same wording is in the comment at `deploy/proxy/templates/conf.d/default.conf.template:27`. The remaining reason (a browser cannot set Host for another site) holds.

**Impact:**
A security exception is backed by arguments that are no longer true.

**Remediation:**
Keep only the valid reason and update the template comment the same way, or replace `$host` in the redirect with `${SERVER_NAME}` and drop the exception (the smoke check would still pass).

---

### [LOW] DOC-005: The list of manually bumped versions leaves out UV_VERSION in CI
**Status:** ✅ Fixed (2026-11-19)
**Verification:** hard — grep „UV_VERSION” in docs/faza-3-ops/README.md:33 → 1 and in .github/dependabot.yml → 1; dependabot.yml parses; relative-link check → 0 missing

**ID:** DOC-005
**Location:** `docs/faza-3-ops/README.md:33`
**Category:** Documentation
**Drift-class:** decision
**Fix-policy:** needs-decision

**Problem:**
The report says Dependabot bumps actions, Python dependencies and Dockerfile images, and that scanner images and Ansible versions are bumped by hand. Dependabot's `github-actions` ecosystem updates only `uses:` references, not the env var `UV_VERSION` (`.github/workflows/ci.yml:36`, passed to `setup-uv` at `:51` and `:104`); the same omission is in the comment of `.github/dependabot.yml:1-4`. The uv image in `backend/Dockerfile` is bumped by the `docker` ecosystem, so the two uv versions drift apart. The sentence "Obrazy, skanery i narzędzia są przypięte po digeście albo po pełnym SHA" (`:33`) also overstates the pinning of the Ansible toolchain (SEC-003).

**Impact:**
The uv version in CI stays on 0.13.8 while the image moves on; a `uv.lock` change can pass in one place and fail in the other.

**Remediation:**
Add "uv w CI (`UV_VERSION`)" to the manual list in `:33` and in the `dependabot.yml` comment, to be bumped together with the `ghcr.io/astral-sh/uv` image, and correct the pinning sentence.

---

### [LOW] DOC-006: The make table says the gates exit with code 1, but make returns 2
**Status:** ✅ Fixed (2026-11-19)
**Verification:** hard — grep „kod 1 przy” in README.md → 0; grep „kod wyjścia różny od 0” in README.md → 3 rows; relative-link check → 0 missing

**ID:** DOC-006
**Location:** `README.md:197`
**Category:** Documentation
**Drift-class:** decision
**Fix-policy:** needs-decision

**Problem:**
The rows for `make semgrep`, `make trivy-fs` and `make trivy-images` say „kod 1 przy znalezisku / przy HIGH lub CRITICAL”. Exit 1 is the code of `scripts/scan.sh`; GNU make returns 2 when a recipe fails (`docs/faza-3-ops/dowody/ci.md:96` records 2), and in `scan.sh` code 2 means bad arguments.

**Impact:**
A script or reader that checks `$?` of the make targets reads the gate result wrongly.

**Remediation:**
Change the wording to „kończy się błędem (`scan.sh`: kod 1; `make`: kod 2)”.

---

## Composite

### [LOW] COMP-001: Smoke log-leak checks pass secrets on the command line of grep and report a false leak when the token is empty
**Status:** 🚫 Rejected (2026-11-19) — dissolved into components

**ID:** COMP-001
**Composed-of:** SEC-004, MAINT-003
**Origin:** review
**Location:** `scripts/stack_smoke.sh:354`
**Category:** Composite
**Effort:** easy

**Problem:**
Everywhere else the script keeps secrets out of argv (`post_json` sends bodies on stdin, passwords go to jq through a pipe, cookies through a 0600 file). The two leak checks have no shared helper: each passes the secret as the pattern argument of grep (`:132`, `:355`), and the loop does not guard against empty values.

**Impact:**
While each grep runs, the demo password, `PW_STRONG` and the session token can be read from `/proc/<pid>/cmdline`, which breaks a guarantee the script header and the Ops report both state. After a failed login `TOKEN=""` makes `grep -qF -- ""` match any non-empty `proxy.log`, so a check meant to detect leaks reports one that does not exist.

**Remediation:**

```bash
# One helper with the empty-value guard inside (grep -f with an empty pattern line also matches every line)
log_has_secret() { [[ -n "$2" ]] || return 1; grep -qF -f <(printf '%s\n' "$2") -- "$1"; }
```

Use it at `:132` and in the loop at `:354-358`.

---

## Verification Summary

**Method:** Cross-domain correlation and adversarial review (Cross-Verifier + Challenger)

| Metric | Count |
|---|---|
| Findings verified | 4 |
| False positives removed | 0 |
| Severity adjustments | 2 |
| Cross-analysis findings | 1 |

### Cross-Analysis (Security <-> Quality)

- COMP-001 (rendered above): the two smoke-script findings share one cause.
- SEC-001 and DOC-002: an unpatched container-escape path ends on a host with unfiltered egress, while section 4 says egress is filtered; the cross-verifier proposes fixing the base and docker roles and sections 4, 9 and 13 in one pass.
- SEC-003 and DOC-005: the documented pin inventory is wrong in two places (the Ansible toolchain is pinned for two packages only, `UV_VERSION` is outside every update path).
- MAINT-004 and DOC-006: the three README gate rows misstate both when the gates fail and with which code.
- MAINT-005 and DOC-003: the retirement procedure of the six nginx exceptions points to a table nobody maintains, and the local evidence predates the sixth exception.

### Challenged Findings

- MAINT-001 (letsencrypt duplication): downgraded from MEDIUM to LOW; the plan prescribed the values, the override is unlikely and the failure is mostly loud.
- DOC-003 (trivy evidence): downgraded from MEDIUM to LOW; the local gate output is identical with five or six entries and CI covers the sixth.
- Quality finding "smoke script secrets in grep argv" was a duplicate of SEC-004 and was merged.
- SEC-001, DOC-001 and DOC-002 were confirmed against the code and the documentation.

### Rejected by auditors (self-falsification)

- Rate-limit bypass with path variants — tested on the live stack, nginx normalises to the exact location; the variants never reach Argon2 unthrottled.
- WAF bypass with a missing or non-JSON Content-Type — tested, fails closed (403).
- Abuse of the password-field exclusion — the regex is anchored to login and register only.
- Open redirect through `$host` in the HTTP to HTTPS redirect — Host cannot be set from another site; triaged (see DOC-004 for the stale rationale).
- Cookies or passwords in the ModSecurity audit log — parts are `AHZ`; checked.
- `/metrics/nginx` exposure or spoofing — external requests get 403.
- ACME exception letting `../` skip the TLS redirect — tested, normalised `$uri` keeps the redirect.
- Six nginx CVE exceptions in `.trivyignore` — documented accepted risk; the mitigation claims were verified (`http2 off`, no quic, mail, stream, ssi or mirror); CVE-2026-118899 is described as exploitable.
- Documented accepted risks (writable proxy filesystem, proxy egress, docker group equals root, GHCR token in config.json, SSH open to all sources by default, `ExecStop` without the `-` prefix, handler order, world-writable `.venv/.lock`) — recorded in section 13.
- Static proxy IP collision, Docker apt key without fingerprint pinning, scanner skip directories, `docker logout` skipped on push failure — not a finding.
- Quality: repeated base-image digests, tag recomputed in `publish`, hard-coded healthcheck port, `__Host-` literal in the cookie pattern, `python3-debian` in the base role, length of `stack_smoke.sh`, `dev_cert.sh` hiding stderr, `make scan` under `-j`, literal `__Host-session` in smoke, helper duplication in `test_cookie_name.py` — plan-prescribed or accepted.
- Documentation: all 14 docs-drift pre-pass hits were checked and none is drift; triage line numbers record scan-time positions; ci.md run counts; `contents: read` wording; Phase 2 endpoint table cookie name; task-to-commit table.

### Doctrine-gap candidates

- No requirement for signing, provenance or an SBOM of the published images.
- Semgrep rule packs are fetched unpinned from the registry at scan time (the only scanner input not pinned).
- No patch schedule for host packages from third-party apt repositories (the concrete case is SEC-001).
- Infrastructure linting (shellcheck, actionlint) is not part of `make lint` or CI; both pass today.
- No automated check that the pinned-versions table matches the code.
- Exception rationales are not re-checked when the facts they cite change (DOC-004).
- Evidence indexes do not record the configuration state at collection time (DOC-003).

### Out of scope (scope check)

None.
