# Results: re-test after the final fixes (Task 12)

Plan: `docs/testing/plans/2026-11-27-patchpoint-final-test-plan.md`. Date: 2026-11-28. Branch: `delivery/patchpoint-final-testing`, head `8fd2c1ccce5efb753641dad716579aeec4568497` (`8fd2c1c`), which contains the fixes of Task 7, Task 8, Task 9 and the documentation of Task 11. Run suffix `$SFX` = `d1b129`. Images: `patchpoint-api:local` = `sha256:0f10c702…` (built with `docker build --no-cache`, then `make images`) and `patchpoint-proxy:local` = `sha256:b9913f3b…`, both built from this head, i.e. after Tasks 7–9. Instances `dev` (18100) and `workers` (18101) were started with `make run`; the stack was compose project `patchpoint-final` in local mode (HTTP 127.0.0.1:28080, HTTPS 127.0.0.1:28443, subnet 10.253.0.0/24), freshly created with a new `api-data` volume and removed with `docker compose down -v`. All evidence is in `retest.txt` (sections as named below); the full gate outputs overwrite `docs/faza-3-ops/dowody/*.txt`.

**Scenarios repeated** (selection per the fix map; the others are not repeated):

- always: OPS-01 in full, BE-02 and BE-03 on `dev`;
- Task 7 (SQLite WAL, baseline B1): BE-05 on `dev`; OPS-09 and OPS-10 on a fresh stack;
- Task 8 (Argon2 concurrency limit, baseline B2): OPS-05 on a fresh stack;
- Task 9 (`--workers 1`, baseline B3): BE-06 on `workers`;
- Task 10 (Ansible role fixes): **skipped**, so OPS-17 was not repeated. OPS-17 passed all its checks a)–j) in the baseline (`results-ansible.md`), so no role code was changed and there is no after-fix retest of its own.

| ID | Baseline | After fixes | Fix commit | Evidence |
|---|---|---|---|---|
| OPS-01 | Pass (145 passed, 28 `[OK]`) | Pass (148 passed, 29 `[OK]`) | none (gate; the +3 tests and +1 smoke check come from Tasks 7–9) | `retest.txt`, `## OPS-01` and `## OPS-01 summary lines`; `docs/faza-3-ops/dowody/*.txt` |
| BE-02 | Pass | Pass | none (always repeated) | `retest.txt`, `## BE-02` |
| BE-03 | Pass | Pass | none (always repeated) | `retest.txt`, `## BE-03` |
| BE-05 | Fail | Pass | `b4f78c2` (Task 7) | `retest.txt`, `## BE-05` |
| BE-06 | Fail | Pass | `054bab4` (Task 9) | `retest.txt`, `## BE-06` |
| OPS-05 | Fail | Pass | `b27c49f` (Task 8) | `retest.txt`, `## Setup` and `## OPS-05` |
| OPS-09 | Pass | Pass | `b4f78c2` (Task 7; the §10 backup command now sets `PRAGMA journal_mode = DELETE`, `8fd2c1c`) | `retest.txt`, `## OPS-09` |
| OPS-10 | Pass | Pass | `b4f78c2` (Task 7; restore commands from §10, `8fd2c1c`) | `retest.txt`, `## OPS-10` |
| OPS-17 | Pass | not repeated (Task 10 skipped) | none | `ops-17-ansible.txt`, `results-ansible.md` (baseline) |

No scenario failed after the fixes, so there is no new `Fail` entry.

## Details per scenario

**OPS-01** — every one of the 13 commands exits with 0. `make test`: `148 passed`, `TOTAL` 98% (98.34%, gate 80%) — the plan's `145 passed` is the baseline count; Tasks 7, 8 and 9 added 3 tests (`test_auth_concurrency.py` 4 → 5, `test_database.py` 13 → 15). Semgrep: 275 rules on 71 files, 0 findings, `.errors | length` = 0. Trivy fs: `brak znalezisk HIGH i CRITICAL` (0 vulnerabilities in `backend/uv.lock` and `deploy/ansible/tools/uv.lock`, 0 misconfigurations in both Dockerfiles). ShellCheck (5 scripts), actionlint and ansible-lint (`Passed: 0 failure(s), 0 warning(s) in 28 files processed of 29 encountered`, then `--syntax-check`) clean. Trivy images: API (debian 13.8) and proxy (alpine 3.24.4) both `brak znalezisk HIGH i CRITICAL` with an empty `.trivyignore`; no new HIGH/CRITICAL appeared, so nothing was ignored or bumped. Smoke: 29 `[OK]`, 0 `[BŁĄD]`, `22 × [NAPRAWIONE]`, the new check `obraz API uruchamia jeden proces uvicorn także przy WEB_CONCURRENCY=4` (Task 9) and the last line `STACK SMOKE ZAKOŃCZONY POWODZENIEM`. Image sizes 254 MB (API) and 158 MB (proxy), unchanged. Unchanged byte for byte against the committed files: `jakosc.txt`, `trivy-fs.txt`, `trivy-obrazy.txt`, `ansible-lint.txt`; the other `dowody` files differ in the numbers above, in the OCI `revision` label of the images (`7ceb48c…` → `8fd2c1c…`), in the smoke date and in `semgrep.txt` only by the count of files matching `.semgrepignore` (62 → 80, because more `docs/` files exist).

**BE-02** — `be02a`: 20×200 + 20×201, none ≥ 500 or `000`, p50/p95/max 0.425/0.664/0.670 s (baseline 0.216/0.280/0.295 s). `be02b`: 40×201, p50/p95/max 0.0021/0.0030/0.0093 s. `users` 43, `tickets` 43, `internal_error` count 0. `PRAGMA journal_mode` on `dev` reads `wal` (baseline `delete`). Edge a): 20×401 "Invalid username or password", p50/p95/max 0.222/0.342/0.361 s (baseline 0.187/0.236/0.264 s). The login latency under 20–40 simultaneous hashes is higher than in the baseline because the API now computes at most 4 Argon2 hashes at a time (Task 8).

**BE-03** — 5×401 "Invalid username or password" and 15×429 "Too many failed login attempts. Try again later." with `Retry-After: 900` on all 15; `login_failures` count 5. Edge a) correct password afterwards: 429 with the same text. Edge b) `p01` login: 200.

**BE-05** — Expected: login 401 in < 1.0 s, every health 200 in < 1.0 s, registration 201 in < 1.0 s, no `internal_error`. Actual (the reader holds `BEGIN` + `SELECT` from t=0 to t≈15; evidence `retest.txt`, `## BE-05`):

```
$ sqlite3 -readonly "$RUN/dev/patchpoint.db" "PRAGMA journal_mode"
wal
# edge a) control without the reader: 401 0.042112
# Run 1 (login in the foreground)
t=1.0 login(wrong pw) started: 401 0.037344s detail="Invalid username or password"
t=1.5 health#1 started: 200 0.001350s   … health#5 (t=5.5): 200 0.001398s
t=7.0 register wal2 started: 201 0.038038s
# Run 2 (login in the background)
t=1.0 login(wrong pw) started: 401 0.040843s detail="Invalid username or password"
t=1.5 health#1 started: 200 0.001322s   … health#5 (t=5.5): 200 0.002115s
t=7.0 register wal3 started: 201 0.042349s
$ grep -c internal_error "$RUN/dev/api.log" || true
0
```

Both variants of the baseline were run. The baseline failure (500 after 5.0 s, stalled health requests, 3 `internal_error` lines) is gone: the longest request took 0.042 s and the log has no `internal_error`.

**BE-06** — Expected: exactly 1 server process; 5×401 and 15×429; count 5; 40×201. Actual (instance `workers`, `WEB_CONCURRENCY=4` in the environment of the uvicorn process, verified in `/proc/<pid>/environ`):

```
$ grep -c "Started server process" $RUN/workers/api.log; grep -E "Started (parent|server) process|Uvicorn running|Started reloader|^cd backend" $RUN/workers/api.log | cut -c1-160
1
cd backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 18101 --workers 1 --no-proxy-headers
INFO:     Started server process [147641]
INFO:     Uvicorn running on http://127.0.0.1:18101 (Press CTRL+C to quit)
```

There is no child process of the server (0 processes with its PID as parent; baseline: parent + 4 workers). The wave of 20 wrong logins gave 5×401 and 15×429, `login_failures` count 5; the 40 registrations gave 40×201 (p50/p95/max 0.237/0.385/0.394 s), `users` 41, no `internal_error`. Edge a) control on `dev`: 5×401 + 15×429, count 5.

**OPS-05** — Expected: 40×201; 40×200 with no `000` and no status ≥ 500; `false <RC0> running`; highest sampled memory < 1 GiB. Actual (fresh stack, `RC0` = 0; evidence `retest.txt`, `## OPS-05`):

```
$ cat "$RUN/oom/reg.out" | sort | uniq -c
     40 201
$ echo "login.out lines: …"; cut -d" " -f1 "$RUN/oom/login.out" | sort | uniq -c; …
login.out lines: 40
     40 200
seconds p50=5.360788 p95=9.870499 max=9.974495
$ docker inspect -f "{{.State.OOMKilled}} {{.RestartCount}} {{.State.Status}}" patchpoint-final-api-1
false 0 running
```

Memory: highest `docker stats` sample 313.6 MiB (9 samples about 2 s apart over the 17.6 s client run; the baseline sampled 406.5 MiB and missed the kill). Because one `docker stats --no-stream` call takes about 2 s, a supplementary sampler read `memory.current` of the API cgroup through `docker exec` in a tight loop: highest 309.8 MiB over 60 samples in the same 17.6 s window. The cgroup's own `memory.peak` after the run is 334565376 bytes (319.1 MiB) against `memory.max` 1073741824, and `memory.events` shows `oom 0` and `oom_kill 0`; `docker events` has no `oom` or `die` event, the kernel log has no OOM line, and the API log has one `Started server process` and 40 `login_succeeded`. The baseline (12×200, 28×`000`, `RestartCount` 0 → 1, kernel OOM kill at 1.04 GB RSS) did not recur. Edge a) 12 parallel wrong logins through the proxy: 5×401 and 7×429 (6 proxy `Too many requests, try again later` plus 1 API lockout `Too many failed login attempts. Try again later.` with `Retry-After` 900), no 502 or 504. The 40 parallel logins now take longer (p50 5.4 s, max 10.0 s against 4.4 s in the baseline, where most of them were killed) because the hashes run at most 4 at a time on the 1-CPU container.

**OPS-09** — The three §10 commands (read from `docs/faza-3-ops/README.md:265-267`, with ` --project-directory /opt/patchpoint` dropped and the copy target replaced by `$RUN/backup/patchpoint.db`) exit with 0. `PRAGMA integrity_check` on the copy prints `ok`; the backup's `journal_mode` is `delete` (the live database is `wal`); backup and live counts are both `users|43 tickets|4 comments|2` and `diff` finds no difference; the backup contains the ticket `backup-marker-d1b129`; `/data/backup.db exists: False` and `ls -l /data` lists only `patchpoint.db`.

**OPS-10** — a) After `docker compose down` / `up -d --wait` the counts are unchanged (43/4/2) and the `.m01` login returns 200. b) After the restore procedure (the seven commands of `docs/faza-3-ops/README.md:275-281`, with ` --project-directory /opt/patchpoint` dropped, `patchpoint_api-data` → `patchpoint-final_api-data`, `/tmp/patchpoint-restore` → `$RUN/restore` and the backup file → `$RUN/backup/patchpoint.db`) the stack is healthy, the counts equal the backup counts (43/4/2), `PRAGMA integrity_check` on the restored live file prints `ok` and its `journal_mode` is `wal` again, the pre-restore `.m01` session returns 401 (created after the backup), `.m01` signs in again (200), the search for `restore-marker-d1b129` finds 0 rows and for `backup-marker-d1b129` 1 row, and the `.m02` login returns 200.

## Notes

- **OPS-09 harness error, repeated.** In the first OPS-09 attempt the loop that executed the three §10 lines read them from stdin, so `docker compose exec` consumed the rest of the input and only the first command (the backup) ran, leaving `/data/backup.db` in place. This was an error of my script, not of §10. The evidence keeps the failed attempt (including the two `Parse error` lines that follow from the missing copy), then removes the leftover `/data/backup.db` and repeats all three commands from the start with the lines on a separate file descriptor; the verdict rests on the repeated run.
- **OPS-05 sampler.** The last line of `mem.txt` is a timestamp without a value (the final sample after the client finished); the verdict does not depend on it.
- **Pacing.** `sleep 7` before every authentication request through the proxy and 65 s after the OPS-05 edge a) burst; BE-02/03/05/06 ran directly against the dev instances (no proxy).
- **Not touched.** The compose project `patchpoint` (`patchpoint-api-1`, `patchpoint-proxy-1`), the kind cluster `secure-k8s-aiops-*` and `vina-searxng` were running before and after. `make stack-smoke` used its own project `patchpoint-smoke` and left nothing behind. After the run there are no `patchpoint-final-*`, `patchpoint-smoke*`, `pp-ansible-target` or `pp-verify-*` containers, no `patchpoint-final_*` or `pp-ansible-docker` volumes, and no listener on 18100–18102, 28080, 28443 or 2222 (`retest.txt`, `## Teardown`).
