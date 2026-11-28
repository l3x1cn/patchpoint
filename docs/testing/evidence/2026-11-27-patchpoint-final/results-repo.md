# Results: repository, supply chain and static Ansible (Task 5)

Plan: `docs/testing/plans/2026-11-27-patchpoint-final-test-plan.md`. Date: 2026-11-28 (local time). Branch: `delivery/patchpoint-final-testing`, head `cb1bf735664e0f9b1909b4feda4b13cfac3478fe`. Run suffix `$SFX` = `536d0a`. Scenarios OPS-11 → OPS-16 ran in this order from the repository root; none of them uses the stack or an API instance. Tools: gitleaks v8.30.1 (`zricethezav/gitleaks@sha256:c00b6bd0…`), KICS v2.2.1 (`checkmarx/kics@sha256:49ccc54b…`), Semgrep 1.185.0 (`semgrep/semgrep@sha256:67518c17…`), uv 0.13.8 with the locked `deploy/ansible/tools` project (Ansible on Python 3.13), `debian:trixie-slim@sha256:8aa5a7bf…` with the Debian `nftables` package, host OpenSSL, `gh` logged in as `l3x1cn`. All images were used by the digest pinned in the scenario; no unpinned tag was substituted. All evidence is in `ops-repo.txt` (sections `## OPS-11` … `## OPS-16`), `gitleaks.json` and `kics-summary.txt` in this directory.

| ID | Kind | Verdict | Evidence | Notes |
|---|---|---|---|---|
| OPS-11 | probe and contract | Confirmed (probe); Pass (contract) | `ops-repo.txt` `## OPS-11`; `gitleaks.json` | Remark claim confirmed: `grep -nE 'gitleaks\|trufflehog' .github/workflows/ci.yml scripts/scan.sh` printed nothing (exit 1), so neither CI nor `scripts/scan.sh` scans the history. Contract passed: `git log --all --format=%h -- .av/secrets.local.env .api.env .env deploy/ansible/inventory.yml deploy/ansible/group_vars/patchpoint/vault.yml` printed nothing (exit 0). A one-off gitleaks scan of the whole history (47 commits, `--log-opts=--all --redact`) exited 1 with 2 findings, both `false positive` (table below). `gh repo view --json visibility --jq .visibility` printed `PUBLIC`. No true positive, so no rotation is needed. |
| OPS-12 | probe | Confirmed | `ops-repo.txt` `## OPS-12`; `kics-summary.txt` | Remark claim confirmed: `grep -nE 'kics\|checkov' .github/workflows/ci.yml` printed nothing (exit 1); no IaC scanner other than Trivy `misconfig` runs in CI. A one-off KICS scan of `compose.yaml`, both Dockerfiles, `deploy/ansible` and `.github/workflows` (14 files, 787 lines, 675 queries, 0 failed) reports CRITICAL 0, HIGH 0, MEDIUM 2, LOW 1, INFO 1. Both MEDIUM findings and the two others are `false positive` (table below); there is no `new defect`. |
| OPS-13 | probe | Confirmed | `ops-repo.txt` `## OPS-13` | The Semgrep run with `--network none` and the exact arguments of `scripts/scan.sh` exited with 2 and no `semgrep.json` was written (`ls -l "$RUN/sg"` → `total 0`). The error names the failed configuration download of the first pack: `HTTPSConnectionPool(host='semgrep.dev', port=443): Max retries exceeded with url: /c/p/python (Caused by NameResolutionError(… Failed to resolve 'semgrep.dev' …))`. The rule packs are therefore fetched from `semgrep.dev` at scan time. |
| OPS-14 | contract and probe | Pass (contract); Confirmed (probes) | `ops-repo.txt` `## OPS-14` | Contract: all 5 `^FROM` lines (3 in `backend/Dockerfile`, 2 in `deploy/proxy/Dockerfile`) carry `@sha256:`; all 4 `*_IMAGE="…"` lines of `scripts/scan.sh` carry `@sha256:`; all 13 `uses:` lines of `ci.yml` end with `@<40 hex> # v…`; `.trivyignore` has no content line (only comments). Probes: `grep -nE '^\s*schedule:' .github/workflows/ci.yml` and `grep -niE 'sbom\|syft\|cosign\|attest' .github/workflows/ci.yml` both printed nothing, so no scheduled scan (R3.3) and no SBOM or signature (R3.1) exist: `Confirmed`. The anonymous token request to `ghcr.io/token?scope=repository:l3x1cn/patchpoint/api:pull` returned HTTP 401 `{"errors":[{"code":"UNAUTHORIZED","message":"authentication required"}]}` (no token; keys of the body: `errors`). The publish job of run 44694936930 (job id `136150145480`) logged `sha-7ceb48c: digest: sha256:f6c2a258…` (size 2205) and `sha-7ceb48c: digest: sha256:cf65b3da…` (size 6773). |
| OPS-15 | contract | Fail | `ops-repo.txt` `## OPS-15` | Two of the five checks disagree (LOW, documentation): `.github/workflows/ci.yml:14` calls the repository private, but it is `PUBLIC`; `docs/faza-3-ops/README.md:319` and `:328` say the GHCR publish was not checked, but run 44694936930 on `main` ran `publish` with `success`. The other three checks agree (the two Faza 3 QA files are tracked, `dowody/ci.md` mentions 44694936930 at `:23` and `:27`, `docs/testing/reports/x.md` is not ignored). Triggers fix B5 (Task 11). |
| OPS-16 | contract and probe | Pass (contract); Confirmed (probes) | `ops-repo.txt` `## OPS-16` | Contract: both renders exit 0 and both `nft -c` runs exit 0; `example.conf` has `ip saddr { 198.51.100.0/24 } tcp dport 22 accept` and no `ip6 saddr` (count 0); the certificate for `helpdesk.example.com` has `DNS:helpdesk.example.com`, `X509v3 Basic Constraints: critical` / `CA:FALSE` and `TLS Web Server Authentication`. Probes: `defaults.conf` has `ip saddr { 0.0.0.0/0 } tcp dport 22 accept` (line 19) and `ip6 saddr { ::/0 } tcp dport 22 accept` (line 20): SSH is open to the Internet by default, documented in `docs/faza-3-ops/README.md:83` (§4); `grep -rniE 'fail2ban\|sshguard\|crowdsec' deploy/ README.md docs/faza-3-ops/README.md` printed nothing (exit 1): no brute-force limiter. |

## Expected / Actual of every Fail and Confirmed

**OPS-11** — Expected: contract `git log` output empty; probe `Confirmed` if the grep is empty; every gitleaks finding triaged. — Actual: `git log` empty; the grep is empty; 2 gitleaks findings, both false positives. File `ops-repo.txt`, section `## OPS-11`:

```
$ grep -nE 'gitleaks|trufflehog' .github/workflows/ci.yml scripts/scan.sh
[exit code: 1]

$ git log --all --format=%h -- .av/secrets.local.env .api.env .env deploy/ansible/inventory.yml deploy/ansible/group_vars/patchpoint/vault.yml
[exit code: 0]

$ gh repo view --json visibility --jq .visibility
PUBLIC
[exit code: 0]
```

Gitleaks (exit 1, `INF 47 commits scanned.`, `WRN leaks found: 2`); the redacted report is copied to `gitleaks.json`:

| # | Rule | File | Commit | Classification |
|---|---|---|---|---|
| 1 | `generic-api-key` | `backend/tests/test_database.py:41` | `2ec8789` (2026-11-16, `fix(backend): secure passwords, sessions, login and demo accounts`) | false positive: the line is `assert not verify_password("password123", "482c811da5d5b4bc6d497ffa98491e38")` in `test_legacy_md5_hash_is_rejected`; `482c811d…` is the MD5 of the well-known test string `password123` (`printf "%s" password123 \| md5sum` → `482c811da5d5b4bc6d497ffa98491e38`), used as an input that the verifier must reject. It is not a credential of any system; the file still has the line at HEAD. |
| 2 | `generic-api-key` | `docs/plans/2026-11-16-faza-2-sec.md:606` | `8eb6141` (2026-11-16, `docs: add delivery plan faza-2-sec`) | false positive: the plan text describes the same test (`` `test_legacy_md5_hash_is_rejected` — `verify_password("password123", "482c811da5d5b4bc6d497ffa98491e38")` daje `False`; ``), the same non-secret test input. |

**OPS-12** — Expected: `Confirmed` if the grep is empty; every HIGH and MEDIUM finding classified. — Actual: the grep is empty; 0 HIGH, 2 MEDIUM. File `ops-repo.txt`, section `## OPS-12`, and `kics-summary.txt`:

```
$ grep -nE 'kics|checkov' .github/workflows/ci.yml
[exit code: 1]
```

```
{"CRITICAL":0,"HIGH":0,"INFO":1,"LOW":1,"MEDIUM":2,"TRACE":0}
MEDIUM	Healthcheck Not Set	compose.yaml	18	services.api
MEDIUM	Healthcheck Not Set	compose.yaml	49	services.proxy
LOW	Logging of Sensitive Data In Defaults	deploy/ansible/ansible.cfg	2	defaults
INFO	Shared Volumes Between Containers	compose.yaml	32	services.api.volumes
```

| Severity | Query | File:line | Classification |
|---|---|---|---|
| MEDIUM | Healthcheck Not Set | `compose.yaml:18` (`services.api`) | false positive: the `HEALTHCHECK` is defined in the image (`backend/Dockerfile:40`) and compose inherits it; the running stack of Task 3/4 reports `Up … (healthy)` for `patchpoint-final-api-1`. Documented in `docs/faza-3-ops/README.md` §5 (HEALTHCHECK row, `:109`). |
| MEDIUM | Healthcheck Not Set | `compose.yaml:49` (`services.proxy`) | false positive: the `HEALTHCHECK` is defined in the image (`deploy/proxy/Dockerfile:60`; it replaces the base image check, `:59`) and the proxy reports `(healthy)`; §5 `:109`. The limits of that check (a hung worker is only marked `unhealthy`) are documented in §13 `:317`. |
| LOW | Logging of Sensitive Data In Defaults | `deploy/ansible/ansible.cfg:2` | false positive: the query asks for a global `no_log` default; the sensitive tasks carry `no_log: true` individually (`deploy/ansible/roles/patchpoint/tasks/main.yml:60` for the API secrets, `:101` for the GHCR login). Not required by the scenario (below MEDIUM), classified for completeness. |
| INFO | Shared Volumes Between Containers | `compose.yaml:32` (`services.api.volumes`) | false positive: `api-data` is mounted only by the `api` service (`grep -n 'api-data' compose.yaml` → lines 5, 32, 93); no second container shares it. Below MEDIUM, classified for completeness. |

**OPS-13** — Expected (`Confirmed` if): exit code not 0 and the output names a failed configuration download. — Actual: exit code 2 and the output names the failed download of `p/python`. File `ops-repo.txt`, section `## OPS-13`:

```
HTTPSConnectionPool(host='semgrep.dev', port=443): Max retries exceeded with url: /c/p/python (Caused by NameResolutionError("HTTPSConnection(host='semgrep.dev', port=443): Failed to resolve 'semgrep.dev' ([Errno -3] Try again)"))
… [112 lines omitted: Python traceback …]
requests.exceptions.ConnectionError: HTTPSConnectionPool(host='semgrep.dev', port=443): Max retries exceeded with url: /c/p/python (Caused by NameResolutionError("HTTPSConnection(host='semgrep.dev', port=443): Failed to resolve 'semgrep.dev' ([Errno -3] Try again)"))
[exit code: 2]
```

This confirms that `make semgrep` needs network access to `semgrep.dev` at scan time (the run took ~118 s because of retries). A missing capability of §3 of the review (R3.2): no QA-NNN.

**OPS-14** — Expected (`Confirmed` if): `schedule:` grep empty; `sbom|syft|cosign|attest` grep empty; the anonymous token request returns no token. — Actual: both greps are empty and the request returned HTTP 401. File `ops-repo.txt`, section `## OPS-14`:

```
$ grep -nE '^\s*schedule:' .github/workflows/ci.yml
[exit code: 1]

$ grep -niE 'sbom|syft|cosign|attest' .github/workflows/ci.yml
[exit code: 1]

$ curl -s --noproxy '*' -m 30 -w '\nHTTP %{http_code}\n' 'https://ghcr.io/token?scope=repository:l3x1cn/patchpoint/api:pull'
{"errors":[{"code":"UNAUTHORIZED","message":"authentication required"}]}

HTTP 401
```

Missing capabilities of §3 of the review (R3.1, R3.3): no QA-NNN. The contract checks (digests, SHA-pinned actions, empty `.trivyignore`) passed.

**OPS-15** — Expected: everything agrees. — Actual: the first two checks disagree. File `ops-repo.txt`, section `## OPS-15`:

```
$ gh repo view --json visibility --jq .visibility
PUBLIC
[exit code: 0]

$ sed -n 11,16p .github/workflows/ci.yml
…
# akcji Trivy z Marketplace (CVE-2026-33634). Repozytorium jest prywatne bez GitHub Advanced Security, więc
# SARIF trafia do artefaktów, nie do code scanning. …

$ sed -n 328p docs/faza-3-ops/README.md
- Publikacja w GHCR (`publish`) zostanie sprawdzona dopiero po scaleniu do `main`.
[exit code: 0]

$ gh run view 44694936930 --json jobs --jq '.jobs[] | select(.name == "publish") | {name, conclusion}'
{"conclusion":"success","name":"publish"}
[exit code: 0]
```

`docs/faza-3-ops/README.md:319` says the digest read in `publish` and the deployment by digest "nie zostały sprawdzone na GHCR ani na serwerze (publikacja możliwa dopiero po scaleniu do `main`)", while run 44694936930 (event `push`, branch `main`, head `7ceb48c25e609eafdf990699e2235a52d78de77d`) ran `publish` with `success` and logged the two `digest: sha256:…` lines recorded in OPS-14 (the deployment by digest on a server remains unchecked, as the text says). Severity LOW (documentation).

**OPS-16** — Expected (`Confirmed` if): `defaults.conf` has the two `0.0.0.0/0` and `::/0` rules; the grep for fail2ban/sshguard/crowdsec is empty. — Actual: both hold. File `ops-repo.txt`, section `## OPS-16`:

```
$ grep -n "tcp dport 22 accept" "$RUN/nft/defaults.conf" "$RUN/nft/example.conf"
/tmp/pp-final.Qfwisf/nft/defaults.conf:19:    ip saddr { 0.0.0.0/0 } tcp dport 22 accept
/tmp/pp-final.Qfwisf/nft/defaults.conf:20:    ip6 saddr { ::/0 } tcp dport 22 accept
/tmp/pp-final.Qfwisf/nft/example.conf:19:    ip saddr { 198.51.100.0/24 } tcp dport 22 accept
[exit code: 0]

$ grep -rniE 'fail2ban|sshguard|crowdsec' deploy/ README.md docs/faza-3-ops/README.md
[exit code: 1]
```

SSH is open to the Internet by default (`deploy/ansible/roles/base/defaults/main.yml:11-14`), documented in `docs/faza-3-ops/README.md:83` (§4: "domyślnie cały Internet, do zawężenia w inventory"); nothing limits brute force beyond `maxauthtries 3` and key-only login. Missing capability of §3 of the review (R3.7): no QA-NNN.

## Deviations from the plan

- **Recording helper.** Every block of `ops-repo.txt` was produced by a small shell function that prints `$ <command>`, runs the command with `eval`, appends its output and the real exit code. The commands are as listed in the plan; the quoting inside `'…'` of the helper differs only for the `nft` and `ansible` blocks (`'"'"'`), which the shell resolves to the plan's text.
- **Abbreviations in the evidence** (each marked `… [N lines omitted: …]`): the layer-by-layer pull progress of the KICS image (56 lines), the KICS ASCII banner (22 lines) and progress bar (1 line), and the 112-line Python traceback of the Semgrep run. The first and last lines of the traceback stay. The KICS output block between those lines is complete.
- **Image pulls.** The plan's digests resolved. The gitleaks and Semgrep images were already present locally for those digests (`Status: Image is up to date`); the KICS image was downloaded (`Status: Downloaded newer image`). The `docker pull` lines are recorded in the evidence.
- **gitleaks.** The `git` subcommand exists in v8.30.1, so the `detect` fallback was not needed. The report keeps the commit author names and e-mail addresses that gitleaks writes (public git metadata); the secret value is `REDACTED`, and the `Match` field of both findings contains the non-secret test string `password123`.
- **KICS.** No flag was rejected. `kics-summary.txt` lists, besides the required counters and HIGH/MEDIUM queries, the LOW and INFO query too, for completeness. The full `kics.json` stayed in `$RUN`.
- **OPS-13.** The command ran for ~118 s (DNS retries) and was moved to the background by the shell; its output and exit code are unchanged. `ls -l "$RUN/sg"` was run once more afterwards and is recorded (`total 0`), because the first listing was not captured in the evidence.
- **OPS-14.** The workflow run `44694936930` is an older run (jobs `ansible`, `trivy-fs`, `quality`, `semgrep`, `build`, `publish`; no `scripts` job); only its `publish` job was used. The `gh run view … --log` output was filtered with `grep -E 'digest: sha256:'` under `set -o pipefail`; the log lines carry the step name `UNKNOWN STEP`.
- **OPS-16.** The rendering used the plan's `uv run --locked --python 3.13 --project tools ansible localhost …` from `deploy/ansible` and wrote into `$RUN/nft/` (mode `0600`, readable by the container's root). `nft -c` ran in `debian:trixie-slim` with `--cap-add NET_ADMIN`; `apt-get install` printed debconf frontend warnings (noninteractive fallback), kept in the evidence, and exited 0. The certificate step ran the plan's `argv` with `openssl` directly (host OpenSSL), writing into `$RUN/tls/`; the private key was never printed.
- **Repository cleanliness.** The scenarios wrote nothing into tracked paths. The locked `deploy/ansible/tools/.venv` and `deploy/ansible/.ansible` are git-ignored.

## Observations (no verdict of their own)

- **Where the finding triage stands.** No gitleaks true positive exists, so the line `TRUE POSITIVE SECRET IN HISTORY — rotate` is not used.
- **R3.3 / R3.4 are partly one-off.** Both a history scan (gitleaks) and an IaC scan (KICS) ran clean once, but neither is part of `ci.yml` or `scripts/scan.sh`; the claims about the missing automation hold.
- **OPS-13 and determinism (R3.2).** The failure is by design of `p/<pack>` registry configs: the pinned image fixes the engine version only, not the rules.
