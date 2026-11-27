# Results: Ansible roles `base` and `docker` on a systemd container (Task 6)

Plan: `docs/testing/plans/2026-11-27-patchpoint-final-test-plan.md`, scenario OPS-17. Date: 2026-11-28 (local time; the container's journal is in UTC, so it reads 2026-11-27 for the same run). Branch: `delivery/patchpoint-final-testing`, head `ed276c030d4091f54e416b8f695a746472a6e607`. Target: container `pp-ansible-target` (image `pp-ansible-target:test`, Debian GNU/Linux 13 trixie, systemd, `--privileged --cgroupns=private`, host port `127.0.0.1:2222` only, volume `pp-ansible-docker` for the nested `/var/lib/docker`). Host: Docker 29.10.0, cgroup v2, kernel 7.3.4-arch1-2. Ansible ran through `uv run --locked --python 3.13 --project tools ansible-playbook` from `deploy/ansible` with `ANSIBLE_ROLES_PATH=roles` and `ANSIBLE_COLLECTIONS_PATH=.ansible/collections` (the collections were already installed). The playbook `site-test.yml` applies the roles `base` and `docker` to the group `patchpoint` with `become: true`. The nested Docker Engine on the target is 29.10.1 (storage driver `overlayfs`, cgroup driver `systemd`). No role file was modified, and there was no retry: every check ran once against one target.

| ID | Kind | Verdict | Evidence | Notes |
|---|---|---|---|---|
| OPS-17 | contract | Pass | `ops-17-ansible.txt` | All ten checks a)–j) passed on the first and only target: run 1 `ok=19 changed=15 unreachable=0 failed=0`, run 2 `ok=15 changed=0 unreachable=0 failed=0`. The handler `Przeładuj konfigurację systemd` ran before `Przeładuj nftables` (R2.2), `ExecStop` of `nftables` is `-/usr/sbin/nft delete table inet patchpoint_host` (`ignore_errors=yes`, R2.3), and 14 `chain DOCKER*` chains survived `systemctl restart nftables`. No `Need info` condition occurred. |

## Checks a)–j)

| Check | Verdict | Evidence (`ops-17-ansible.txt`) |
|---|---|---|
| a) First run: `failed=0`, `unreachable=0` | Pass | `## a)`: `pp-ansible-target : ok=19 changed=15 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0`, exit code 0 |
| b) Handler order in run 1 | Pass | `## b)`: `RUNNING HANDLER [base : Przeładuj konfigurację systemd]` precedes `RUNNING HANDLER [base : Przeładuj nftables]` |
| c) nftables drop-in | Pass | `## c)`: `DropInPaths=/etc/systemd/system/nftables.service.d/10-patchpoint.conf`; `ExecStop={ path=/usr/sbin/nft ; argv[]=/usr/sbin/nft delete table inet patchpoint_host ; ignore_errors=yes ; … }` |
| d) Services and host table | Pass | `## d)`: `systemctl is-active nftables ssh docker` → `active` ×3; the table has `policy drop` and `ip saddr 0.0.0.0/0 tcp dport 22 accept` |
| e) Docker rules survive an nftables restart | Pass | `## e)`: `N1=14`, `restart-exit=0`, `N2=14` |
| f) `nft delete table …; systemctl stop nftables` | Pass | `## f)`: exit 0, `Result=success`, tables `ip nat`, `ip filter`, `ip6 nat`, `ip6 filter` remain, `systemctl start nftables` restores `table inet patchpoint_host` |
| g) `sshd -T` hardening | Pass | `## g)`: `maxauthtries 3`, `permitrootlogin no`, `passwordauthentication no`, `kbdinteractiveauthentication no`, `x11forwarding no`, `allowtcpforwarding no` |
| h) Firewall seen from another container | Pass | `## h)`: `8081:1` and `22:0` (the listener on 8081 was up: `ss -ltn` shows `0.0.0.0:8081`, and a request from inside the target returned 200) |
| i) apt configuration | Pass | `## i)`: `20auto-upgrades` has `APT::Periodic::Update-Package-Lists "1";` and `APT::Periodic::Unattended-Upgrade "1";`; `apt-config dump` has `Unattended-Upgrade::Origins-Pattern:: "origin=Docker,label=Docker CE";` |
| j) Second run | Pass | `## j)`: `pp-ansible-target : ok=15 changed=0 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0`, exit code 0 |

There is no `Fail`, so no task name is classified as `role defect` or `environment`, and Task 10 (B4) has no trigger.

## Expected / Actual

**OPS-17** — Expected: a)–j) as in the plan. — Actual: all hold. Quoted verdict-deciding lines (file `ops-17-ansible.txt`):

```
$ grep '^RUNNING HANDLER' "$OUT"
RUNNING HANDLER [base : Przeładuj SSH] *****************************************
RUNNING HANDLER [base : Przeładuj konfigurację systemd] ************************
RUNNING HANDLER [base : Przeładuj nftables] ************************************
RUNNING HANDLER [docker : Zrestartuj Dockera] **********************************
[exit code: 0]

$ docker exec pp-ansible-target systemctl show nftables -p DropInPaths -p ExecStop
ExecStop={ path=/usr/sbin/nft ; argv[]=/usr/sbin/nft delete table inet patchpoint_host ; ignore_errors=yes ; start_time=[n/a] ; stop_time=[n/a] ; pid=0 ; code=(null) ; status=0/0 }
DropInPaths=/etc/systemd/system/nftables.service.d/10-patchpoint.conf
[exit code: 0]

N1=14
restart-exit=0
N2=14

$ docker exec pp-ansible-target systemctl show -p Result nftables
Result=success

$ docker run --rm alpine:3.24 sh -c 'nc -z -w 3 172.17.0.3 8081; echo "8081:$?"; nc -z -w 3 172.17.0.3 22; echo "22:$?"'
8081:1
22:0
```

Run 1 recap: `pp-ansible-target : ok=19 changed=15 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0`. Run 2 recap: `pp-ansible-target : ok=15 changed=0 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0`.

## Deviations from the plan

- **Recording helper.** Every block of `ops-17-ansible.txt` was produced by a small shell function that prints `$ <command>`, runs it with `bash -c`, appends its output and the real exit code of that `bash -c` (for a pipeline, the exit code of its last command, unless a block says otherwise with `PIPESTATUS`). The commands are the plan's; those that carry quoting for `docker exec … sh -c '…'` or `$RUN` expansion are written as the helper received them. Two blocks were wrong because of the helper, not because of the target, and were redone: the first `cat "$RUN/at/Dockerfile"` ran before `$RUN` was exported (it printed `cat: /at/Dockerfile: No such file or directory`), and the first check b) ran before `$OUT` was exported (`grep: : No such file or directory`). Both failed blocks were removed from the evidence, and the b) block was reinserted at its place, so the order of the sections is the plan's. A third block, the start of the HTTP listener of check h), was recorded with a stray extra `docker exec … sh -c 'echo before-start'` and was corrected by hand to the single command `docker exec -d pp-ansible-target python3 -m http.server 8081`; its output (empty) and exit code 0 are those of that command.
- **Abbreviation.** The output of `docker build` in the preconditions is cut to its last 25 lines by `tail -n 25` (marked in the evidence; the exit code shown is that of `docker build`). The playbook outputs are complete and verbatim.
- **Wait for the target.** The wait loop (poll every 1 s, at most 120 s) left after 2 s with `degraded`; this is recorded in a comment line of the evidence and with `systemctl is-system-running` (prints `degraded`, exit code 1 by systemd's convention). The failed unit is `systemd-modules-load.service`; its cause was not investigated, and it is not a unit of the roles.
- **Extra evidence.** Besides the plan's checks, the evidence also has: the public-key fingerprint, `ssh` as `admin` with `sudo -n` (`admin` / `root`), the content of the drop-in file and of `/etc/apt/apt.conf.d/52patchpoint-docker`, `ss -ltn` and a local request to the listener of check h), `nft list tables` around check f), the `journalctl -u docker` excerpts used for the `Need info` condition, and `docker info` of the nested engine.
- **`Need info` conditions.** Neither occurred: the target reached `degraded` in 2 s, and `journalctl -u docker -p warning` printed `-- No entries --`. A search for `storage|cgroup|overlay|error` in the unit's journal found only `info`-level lines (`loaded extension … storage.bbolt`, `Deleting nftables IPv4 rules … error=…` for the nonexistent tables `docker-bridges` before the first start, and the graceful restart caused by the handler `Zrestartuj Dockera`).
- **Ansible warning.** Run 1 printed one `[WARNING]: Module remote_tmp /root/.ansible/tmp did not exist and was created with a mode of 0700` at the task `docker : Dodaj repozytorium Docker Engine` (`become` to root over an unprivileged SSH user). It is a warning, not a failure, and does not appear in run 2.
- **The key.** The SSH key pair was generated in `$RUN/at` and never printed (only the fingerprint of the public key is in the evidence). The inventory prints the path of the private key, which lived in the deleted `$RUN`.
- **Host firewall.** The nested Docker and nftables acted in the netns of the target container. Nothing touched the host's firewall, the compose project `patchpoint`, the kind cluster `secure-k8s-aiops-*` or `vina-searxng`.
- **Teardown.** The plan's three commands (`docker rm -f pp-ansible-target`, `docker volume rm pp-ansible-docker`, `docker rmi pp-ansible-target:test`) exited with 0. Afterwards no container named `pp-ansible-target`, `patchpoint-final-*`, `patchpoint-smoke*` or `pp-verify-*`, no volume `pp-ansible-docker` or `patchpoint-final_*` and no listener on 2222 remained (the three `grep` checks exited with 1). The base image `debian:trixie` and the image `alpine:3.24` (pulled for check h)) remain in the local image store; they are not target resources. `$RUN` was deleted.
- **Repository cleanliness.** The scenario wrote nothing into tracked paths; `deploy/ansible/.ansible` and `deploy/ansible/tools/.venv` are git-ignored.

## Observations (no verdict of their own)

- **The role defects that Task 10 anticipates did not occur.** In this run the handler `Przeładuj nftables` (`state: reloaded`) succeeded in run 1, and run 2 did not report a change at `docker : Zainstaluj Docker Engine i Docker Compose` (`update_cache: true` without `cache_valid_time`). Both stayed `ok` / `changed` as required, so no check failed on them.
- **R3.7 (SSH protection) as built.** The host table opens `tcp dport 22` to `0.0.0.0/0` and `::/0` by the role defaults (see OPS-16), accepts `80` and `443`, and drops the rest (`8081:1`); the Docker chains of the nested engine stay in place after `systemctl restart nftables` and after `nft delete table inet patchpoint_host; systemctl stop nftables`.
