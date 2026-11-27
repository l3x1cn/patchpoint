# Results: load, failures and backups on the stack (Task 4)

Plan: `docs/testing/plans/2026-11-27-patchpoint-final-test-plan.md`. Date: 2026-11-28 (local time; container logs are in UTC, so they read 2026-11-27 for the same run). Branch: `delivery/patchpoint-final-testing`, head `8763c21760cb5c19ea95f529b5fa96e7a9ca9098`. Run suffix `$SFX` = `d03aac`. Stack: compose project `patchpoint-final` in local mode (HTTP 127.0.0.1:28080, HTTPS 127.0.0.1:28443, subnet 10.253.0.0/24, images `patchpoint-api:local` = `sha256:7f90ff39…` and `patchpoint-proxy:local` = `sha256:23b42c36…`, both built from HEAD in Task 2), started once with a new `api-data` volume and removed with `docker compose down -v` after OPS-10. All scenarios ran in the order OPS-05 → OPS-10 on that one stack (only OPS-10 stopped and re-created it). The demo password, the 40 `m01`…`m40` passwords and every session value lived only in a private temp directory that was deleted. All evidence is in `ops-resilience-data.txt`.

| ID | Kind | Verdict | Evidence | Notes |
|---|---|---|---|---|
| OPS-05 | contract | Fail | `ops-resilience-data.txt`, sections `## OPS-05` and `## OPS-05 edge a)` | The 40 registrations returned 201, but of the 40 parallel logins only 12 returned 200 and 28 returned `000`: the kernel OOM-killed the API process (`oom` event, exit code 137, `Memory cgroup out of memory: Killed process … (uvicorn) … anon-rss:1042024kB`), and `restart: unless-stopped` started it again (`RestartCount` 0 → 1). The sampled `MemUsage` maximum (406.5 MiB, 8 samples ~2 s apart) missed the peak. Edge a) passed: 12 parallel wrong logins through the proxy gave 5×401 and 7×429 and no 502/504. Triggers fix B2 (Task 8). |
| OPS-06 | contract | Pass | `ops-resilience-data.txt`, section `## OPS-06` | SIGTERM to PID 1 of the API: the polls (every 1 s for 90 s) gave 200 at 0.1 s, one 502 at 1.2 s (0.0033 s), then 200 from 2.2 s to the end; the slowest request took 0.0145 s. API `RestartCount` 1 → 2, proxy `RestartCount` 0 → 0. After a new agent login `GET /api/tickets?limit=100` returned 3 tickets, equal to N0 = 3. |
| OPS-07 | probe | Confirmed | `ops-resilience-data.txt`, section `## OPS-07` | After `pkill -STOP` the 12 nginx workers were in state `T`; the health status reached `unhealthy` between t=95 s and t=110 s and stayed there until the manual restart (t=276 s); `RestartCount` stayed 0 and `State.Status` stayed `running`; every one of the 19 curl calls exited with 28 (`000`). After `docker compose restart proxy` `/api/health` returned 200 within 11 s. |
| OPS-08 | probe and contract | Confirmed (probe); Pass (contract) | `ops-resilience-data.txt`, section `## OPS-08` | Host control `204`. Proxy: `204` (it reaches the Internet). API: `OSError: [Errno 101] Network is unreachable`, exit 1 (the `backend` network is `internal`). |
| OPS-09 | contract | Pass | `ops-resilience-data.txt`, section `## OPS-09` | The three §10 commands exited with 0; `PRAGMA integrity_check` printed `ok`; backup and live counts both `users|43 tickets|4 comments|2` and `diff` found no difference; the backup contains the ticket `backup-marker-d03aac`; `/data/backup.db` no longer exists (`ls -l /data` lists only `patchpoint.db`, `os.path.exists` → `False`). |
| OPS-10 | contract | Pass | `ops-resilience-data.txt`, section `## OPS-10` | a) After `down` / `up` the counts were unchanged (43/4/2) and the `.m01` login returned 200. b) After the restore procedure the stack was healthy, the counts equalled the backup counts (43/4/2), `PRAGMA integrity_check` on the restored file printed `ok`, `.m01` searching for `restore-marker-d03aac` found 0 rows (the ticket made after the backup is gone; `backup-marker-d03aac` found 1 row) and the `.m02` login returned 200. |

## Expected / Actual of every Fail and Confirmed

**OPS-05** — Expected: 40×201 for the registrations; 40×200 for the logins "with no `000` and no status ≥ 500"; `false <RC0> running` (`RC0` = 0); highest sampled memory < 1 GiB. — Actual: registrations 40×201; logins `28 000`, `12 200`; `false 1 running`; highest sampled `MemUsage` 406.5 MiB (the samples missed the kill). File `ops-resilience-data.txt`, section `## OPS-05`:

```
login.out lines: 40
     28 000
     12 200
seconds p50=4.400526 p95=4.409647 max=4.411250
…
$ docker inspect -f "{{.State.OOMKilled}} {{.RestartCount}} {{.State.Status}}" patchpoint-final-api-1
false 1 running
…
1795821524 oom exitCode=
1795821524 die exitCode=137
1795821524 start exitCode=
…
Killed process 453877 (uvicorn) total-vm:4761088kB, anon-rss:1042024kB, file-rss:18412kB
```

Refutation: re-verified: no (single run, not repeated); env: stack `patchpoint-final`; evidence: `ops-resilience-data.txt`. The `false` in `OOMKilled` does not contradict the OOM kill: [INFERENCE: Docker clears `State.OOMKilled` and `ExitCode` when the restart policy starts the container again; `ExitCode=0` and a `FinishedAt` earlier than `StartedAt` in the inspect output are consistent with that]. The kill itself is recorded by the Docker `oom` event, exit code 137 of the `die` event, and the kernel line above. The API log of the restarted container contains the lines `Started server process [1]` twice (start and restart) and only 12 `login_succeeded` events, matching the 12 `200`; no `internal_error` and no Python traceback (the process was killed, not crashed). Known-risk check: 40 parallel Argon2 verifications at 64 MiB each exceed `mem_limit: 1g` (backend/app/security.py:11, compose.yaml:44); the data survived (the same 43 users are present afterwards, see OPS-09). The registrations ran one at a time and did not trigger the kill. Fix B2 (Task 8) is triggered.

**OPS-07** — Expected (`Confirmed` if): health status reaches `unhealthy`; `RestartCount` unchanged and `Status` `running`; curl exits with 28 until the manual restart; after the restart `/api/health` returns 200 within 60 s. — Actual: all four hold. File `ops-resilience-data.txt`, section `## OPS-07`:

```
t=5s inspect: healthy 0 running | curl: 000 exit=28
…
t=95s inspect: healthy 0 running | curl: 000 exit=28
t=110s inspect: unhealthy 0 running | curl: 000 exit=28
…
t=276s inspect: unhealthy 0 running | curl: 000 exit=28
…
restart took 10 s
t=10s curl: 000 exit=56
t=11s curl: 200 exit=0
```

(`docker inspect` after the freeze: `unhealthy 0 running`; the last five health-check log entries all have `exit=-1`.) This confirms the claim in docs/faza-3-ops/README.md §13 (nginx bullet). A missing capability of §3 of the review: no QA-NNN.

**OPS-08** — Expected (`Confirmed` if): the proxy gets 204; contract: the API connection fails; `Need info` if the host control fails. — Actual: host control `204 exit=0`; proxy `204 exit=0`; API `OSError: [Errno 101] Network is unreachable` and `exit=1`. File `ops-resilience-data.txt`, section `## OPS-08`:

```
$ docker compose exec -T proxy curl -s -m 10 -o /dev/null -w "%{http_code}" https://www.google.com/generate_204; echo " exit=$?"
204 exit=0
…
OSError: [Errno 101] Network is unreachable
exit=1
```

(The `[exit code: 0]` printed under the API block is that of the trailing `echo`; the exit code of the Python call is the `exit=1` line.) This confirms the §13 egress bullet. A missing capability of §3 of the review: no QA-NNN.

## Restore commands that worked (OPS-10 b), for Task 11)

Run from the repository root with the stack environment of the plan's Setup exported (`COMPOSE_PROJECT_NAME=patchpoint-final` …); each command exited with 0 and exactly as the plan lists them (nothing needed to deviate):

```bash
docker compose down
docker volume rm patchpoint-final_api-data
install -d -m 0755 "$RUN/restore"
install -m 0644 "$RUN/backup/patchpoint.db" "$RUN/restore/patchpoint.db"
docker compose run --rm --no-deps -T -v "$RUN/restore:/restore:ro" --entrypoint python api -c "import shutil; shutil.copyfile('/restore/patchpoint.db', '/data/patchpoint.db')"
rm -rf "$RUN/restore"
docker compose up -d --wait --wait-timeout 180
```

The new `api-data` volume was created by `docker compose run` (`Volume patchpoint-final_api-data Created`); the copied file was owned by uid 10001 (`-rw-r--r-- 1 10001 10001 49152 … patchpoint.db`, the only file in `/data`), and the API started healthy on it. In production `patchpoint-final_api-data` becomes `patchpoint_api-data` and `$RUN/…` becomes a temporary directory plus the downloaded backup file (as in Task 11 step 3).

## Deviations from the plan

- **Cookie handling.** The session cookie is `Secure`, so curl drops it over `http://patchpoint.localhost:28080` in a jar. Sessions for OPS-06, OPS-09 and OPS-10 were taken from the `Set-Cookie` header of the login response into a header file under `$RUN` (mode 600, passed as `-H @file`, never in argv or in the evidence), as in Task 3. In the evidence the login commands show the awk that writes the file; no value is printed.
- **OPS-05 sampler.** One `docker stats --no-stream` call takes ~1.5–2 s, so the sampler gave 8 samples ~2 s apart (covering the registrations and the logins) instead of one every 0.5 s. The memory verdict therefore rests on the kernel and Docker OOM records, not on the sampled maximum. The `sh -c` script of the client is the plan's, only the shell quoting differs (noted in the evidence).
- **OPS-05 edge a).** The 12 parallel wrong logins used the unregistered login `qa.final.d03aac.edge` (so no account needed for OPS-09/OPS-10 got locked). One of the 429s is the API lockout (`Too many failed login attempts. Try again later.`, `Retry-After` 900) because 5 wrong attempts on any username, registered or not, lock it; the other six 429s come from the proxy.
- **OPS-05 post-check.** The restarted container's cgroup counters (`memory.events` `oom 0`, `oom_kill 0`) are zero because they restarted with the container; they are recorded and are not evidence against the kill.
- **OPS-06 and OPS-05 counters.** OPS-05 restarted the API once, so the OPS-06 baseline for the API was `RestartCount` 1 (the plan anticipates this), and "+1" means 1 → 2.
- **OPS-07 sampling.** Every sample waits for its `curl -m 5` timeout (exit 28) plus the 10 s sleep, so the 19 samples are ~15 s apart and span 276 s instead of 19 samples at 10 s over 180 s. The `unhealthy` threshold was crossed between t=95 s and t=110 s, inside both windows. The trailing `[exit code: 1]` of that block is the last `[ $i -lt 18 ] && sleep 10` of the loop, not a failure.
- **OPS-09.** `--project-directory /opt/patchpoint` was dropped (the exported Setup env block selects the project), and the file was copied to `$RUN/backup/patchpoint.db` instead of `./patchpoint-$(date +%F).db`. My first counting commands used double-quoted SQL literals, which the `sqlite3` CLI rejects (`Parse error … no such column`); the two failed attempts remain in the evidence and the commands were repeated with single quotes.
- **OPS-10.** After the restore, the `.m01` session created in step a) was gone from the restored database (`GET /api/auth/me` with the old header file returned 401, as it should: that session was created after the backup), so `.m01` signed in again before the search. The final `ls "$RUN/restore"` in the evidence exits with 2 because the directory was removed by the procedure, as intended.
- **Waits.** 65 s after the OPS-05 edge a) burst and `sleep 7` before every proxy-fronted sign-in; the only auth requests through the proxy in this task are those sign-ins and the OPS-05 edge a) wave (an exception to the 7 s rule).

## Observations (no verdict of their own)

- **API recovery after the OOM kill.** The API container came back by itself (restart policy), the proxy resolved the new address without a restart (`RestartCount` 0), and no data was lost; during the outage clients saw connection errors (`000`), not clean 5xx responses, because the process died with the in-flight requests.
- **Health check after `docker compose restart proxy`.** The container's health status reads `starting` for the first seconds and `healthy` again in the next record (`proxy: healthy 0 running` in OPS-08).
