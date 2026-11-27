# Results: baseline gates and development API (Task 2)

Plan: `docs/testing/plans/2026-11-27-patchpoint-final-test-plan.md`. Date: 2026-11-27. Branch: `delivery/patchpoint-final-testing`, head `8f3549879c03696eb639fd4927ea1e92243bd984` (the plan was written at `3d9b40a`; the tree under test is this head). Run suffix `$SFX` = `9943bd`. Instances `dev` (18100), `workers` (18101, `WEB_CONCURRENCY=4`) and `docs` (18102) were started with `make run` and stopped after the scenarios; the databases lived in a private temp directory that was deleted.

| ID | Kind | Verdict | Evidence | Notes |
|---|---|---|---|---|
| OPS-01 | contract | Pass | `ops-01-gates.txt` | All 13 commands exit 0. pytest `145 passed`, `TOTAL` 98% (98.32%, gate 80%). Semgrep: 0 findings, 275 rules on 71 files, `.errors \| length` = 0. Trivy fs, ShellCheck, actionlint, ansible-lint (`--syntax-check` too) clean; Trivy image gates for API and proxy clean. Smoke: 28 `[OK]`, 0 `[BŁĄD]`, `22 × [NAPRAWIONE]`, ends with `STACK SMOKE ZAKOŃCZONY POWODZENIEM`. Images `patchpoint-api:local` and `patchpoint-proxy:local` are kept for later tasks. |
| BE-01 | contract | Pass | `be-dev-api.txt`, section `## BE-01` | `docs`: `/openapi.json` 200 with `info.version` `0.3.0`; `/docs` 200 `text/html; charset=utf-8`. Edge a) `dev`: `/openapi.json` 404. Edge b) `backend/pyproject.toml:3` has `version = "0.3.0"`. |
| BE-02 | contract | Pass | `be-dev-api.txt`, section `## BE-02` | `be02a`: 20×200 + 20×201, none ≥ 500 or `000`; p50/p95/max 0.216/0.280/0.295 s. `be02b`: 40×201; p50/p95/max 0.0020/0.0027/0.0037 s. `users` 43, `tickets` 43, `internal_error` count 0. Edge a): 20×401 "Invalid username or password" (p50/p95/max 0.187/0.236/0.264 s). |
| BE-03 | contract | Pass | `be-dev-api.txt`, section `## BE-03` | 5×401 "Invalid username or password" and 15×429 "Too many failed login attempts. Try again later." with `Retry-After: 900` on all 15; `login_failures` count 5. Edge a) correct password afterwards: 429. Edge b) `p01` login: 200. |
| BE-04 | contract | Pass | `be-dev-api.txt`, section `## BE-04` | Per ticket exactly one 200 and one 400 "Invalid status transition: …" (10×200, 10×400, none ≥ 500); the agent's `GET` shows the status of the 200 request on all 10 tickets. Edge a) `{}` → 400 "Nothing to update". Edge b) employee `PATCH` → 403 "Helpdesk agent role required". |
| BE-05 | contract | Fail | `be-dev-api.txt`, section `## BE-05` and `## Underlying exception …` | `journal_mode` is `delete`. Edge a) (control, no reader): 401 in 0.039 s. With an external read transaction open: the wrong-password login returns 500 after 5.01 s, the registration returns 500 after 5.04 s (run 2) and every health request stalls (4.51 s down to 0.50 s). 3 `internal_error` lines. |
| BE-06 | contract | Fail | `be-dev-api.txt`, section `## BE-06` | `workers` log has 4 `Started server process` lines (one parent + 4 workers), expected 1. The functional expectations held in this run: 5×401 + 15×429, `login_failures` count 5, 40×201 (none ≥ 500); three more rounds with 20 parallel guesses each gave the same 5×401 + 15×429 and count 5, so the count/write race was not observed. Edge a) control on `dev`: 5×401 + 15×429, count 5. |
| BE-07 | probe | Confirmed | `be-dev-api.txt`, section `## BE-07` | All 8 account-management requests as the agent return 404 `{"detail":"Not Found"}`. Edge a) registration with `"role": "agent"` → 422 `extra_forbidden` on `body.role`, 0 users created. Edge b) the only `agent` is `helpdesk`. |
| BE-08 | probe | Confirmed | `be-dev-api.txt`, section `## BE-08` | 2 sessions → logout with A (200 `{"message":"Logged out"}`) → me(A) 401 "Not authenticated", me(B) 200 → 1 session left. Edge a) logout without a cookie: 200 `{"message":"Logged out"}`. |

**BE-05** — Expected: the login with a wrong password returns 401 in < 1.0 s, every health request returns 200 in < 1.0 s, the registration returns 201 in < 1.0 s, and the API log has no `internal_error` (plan, BE-05 Expected). — Actual: the commit blocks on the event-loop thread for the 5 s busy timeout and fails with 500; the stall delays every request. Evidence `be-dev-api.txt`, section `## BE-05`:
```
$ sqlite3 -readonly "$RUN/dev/patchpoint.db" "PRAGMA journal_mode"
delete
# Run 2 (login in the background; the reader holds BEGIN + SELECT from t=0 to t≈15)
t=1.0 login(wrong pw) started: 500 5.009204s detail="Internal server error"
t=1.5 health#1 started: 200 4.508505s
t=2.5 health#2 started: 200 3.505444s
t=3.5 health#3 started: 200 2.501806s
t=4.5 health#4 started: 200 1.498765s
t=5.5 health#5 started: 200 0.496370s
t=7.0 register wal3 started: 500 5.042754s body="Internal server error"
$ grep internal_error "$RUN/dev/api.log" | cut -c1-400
… "event": "internal_error", "exception": "DatabaseError", "method": "POST", "path": "/api/auth/login", "sql": "COMMIT"}   (2×, 23:43:15 and 23:43:51)
… "event": "internal_error", "exception": "DatabaseError", "method": "POST", "path": "/api/auth/register", "sql": "COMMIT"}   (23:43:57)
$ grep -c "sqlite3.OperationalError: database is locked" "$RUN/dev/api.log"
3        (raised by `conn.commit()` in `transaction`, backend/app/database.py:158)
```
In run 1 (login in the foreground, so the later steps were delayed by its 5 s) the login also returned 500 after 5.01 s, the five health requests started at t=6.5–10.5 returned 200 in ≈ 1.4 ms, and the registration at t=11.5 returned 201 after 3.57 s, because the reader released the lock during the wait. The defect is B1 of the fix map (Task 7).

**BE-06** — Expected: exactly 1 server process; 5×401 and 15×429; `login_failures` count 5; 40×201 with none ≥ 500 or `000` (plan, BE-06 Expected). — Actual: 4 server processes; the other expectations held. Evidence `be-dev-api.txt`, section `## BE-06`:
```
$ grep -c "Started server process" $RUN/workers/api.log; grep -E "Started (parent|server) process|Uvicorn running|Started reloader" $RUN/workers/api.log
4
INFO:     Uvicorn running on http://127.0.0.1:18101 (Press CTRL+C to quit)
INFO:     Started parent process [419656]
INFO:     Started server process [419667]
INFO:     Started server process [419669]
INFO:     Started server process [419668]
INFO:     Started server process [419670]
$ wave be06; summary be06
      5 401
     15 429
$ sqlite3 -readonly "$RUN/workers/patchpoint.db" "SELECT COUNT(*) FROM login_failures WHERE username = 'qa.final.9943bd.mp'"
5
```
`make run` (Makefile:22) passes no `--workers`, so uvicorn reads `WEB_CONCURRENCY=4` as its worker count. The defect is B3 of the fix map (Task 9).

**BE-07** — Expected: each of the 8 requests returns 404 `{"detail":"Not Found"}`. — Actual: all 8 returned that. Evidence `be-dev-api.txt`, section `## BE-07`:
```
GET /api/users -> 404 … {"detail":"Not Found"}
POST /api/users -> 404 … {"detail":"Not Found"}
PATCH /api/users/1 -> 404 … {"detail":"Not Found"}
DELETE /api/users/2 -> 404 … {"detail":"Not Found"}
POST /api/auth/password -> 404 … {"detail":"Not Found"}
POST /api/auth/password-reset -> 404 … {"detail":"Not Found"}
POST /api/auth/logout-all -> 404 … {"detail":"Not Found"}
DELETE /api/auth/sessions -> 404 … {"detail":"Not Found"}
```
Only `health`, `auth` and `tickets` routers are included (`backend/app/main.py:106-108`). The registration payload cannot set a role (422 `extra_forbidden`, 0 users created), so the capability is missing without a privilege gap.

**BE-08** — Expected: first count 2; logout 200; me(A) 401; me(B) 200; second count 1. — Actual: as expected. Evidence `be-dev-api.txt`, section `## BE-08`:
```
2
{"message":"Logged out"}
{"detail":"Not authenticated"}
{"username":"qa.final.9943bd.multi","role":"employee"}
1
```
Logout ends only the current session; there is no route that revokes the other sessions of the user.

## Notes

- `$!` after `setsid make run … &` was not the process-group id in this environment (setsid forked), so `kill -TERM -- "-$(cat pgid)"` failed; the groups were found with `ps -o pgid=` and stopped (recorded in `be-dev-api.txt`). The ports 18100–18102 had no listener afterwards.
- BE-05 was run twice because the plan's step list is ambiguous about whether the login blocks the script; run 2 overlaps the health requests with the stalled login, run 1 follows the steps sequentially. Both are in the evidence.
- The user's stack (`patchpoint-api-1`, `patchpoint-proxy-1`), the kind cluster and `vina-searxng` were not touched; `make stack-smoke` used project `patchpoint-smoke`, ports 18000/18080/18443 and subnet 10.251.0.0/24 and left no containers, volumes or networks behind.
