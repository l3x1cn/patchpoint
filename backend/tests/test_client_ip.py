import http.client
import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Final

BACKEND_DIR: Final = Path(__file__).resolve().parents[1]
REPO_ROOT: Final = BACKEND_DIR.parent
FORGED_IP: Final = "203.0.113.77"
LOOPBACK: Final = "127.0.0.1"
STARTUP_TIMEOUT_SECONDS: Final = 30.0


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind((LOOPBACK, 0))
        return int(sock.getsockname()[1])


def _documented_uvicorn_args(port: int) -> list[str]:
    """Arguments `make run` passes to uvicorn, read from the Makefile so the test follows it."""
    make = shutil.which("make")
    assert make is not None, "make is required to read the documented start-up command"
    result = subprocess.run(  # noqa: S603
        [
            make,
            "--no-print-directory",
            "-n",
            "-C",
            str(REPO_ROOT),
            "run",
            f"API_HOST={LOOPBACK}",
            f"API_PORT={port}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    _, marker, arguments = result.stdout.partition(" uvicorn ")
    assert marker, f"`make run` does not start uvicorn: {result.stdout!r}"
    return shlex.split(arguments)


def _wait_until_healthy(server: subprocess.Popen[bytes], port: int) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        assert server.poll() is None, "uvicorn exited before it became healthy"
        connection = http.client.HTTPConnection(LOOPBACK, port, timeout=2)
        try:
            connection.request("GET", "/api/health")
            if connection.getresponse().status == 200:
                return
        except OSError:
            time.sleep(0.2)
        finally:
            connection.close()
    raise AssertionError("uvicorn did not become healthy in time")


@contextmanager
def _documented_server(tmp_path: Path, log_path: Path) -> Iterator[int]:
    port = _free_port()
    env = {**os.environ, "PATCHPOINT_DATABASE_PATH": str(tmp_path / "probe.db")}
    with log_path.open("wb") as log:
        server = subprocess.Popen(  # noqa: S603
            [sys.executable, "-m", "uvicorn", *_documented_uvicorn_args(port)],
            cwd=BACKEND_DIR,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            _wait_until_healthy(server, port)
            yield port
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


def test_forged_forwarded_for_is_not_logged_as_client_ip(tmp_path: Path) -> None:
    """With uvicorn started as `make run` does, a header cannot set client_ip.

    TestClient bypasses uvicorn's proxy-header handling, so this starts the real server.
    """
    log_path = tmp_path / "uvicorn.log"
    with _documented_server(tmp_path, log_path) as port:
        connection = http.client.HTTPConnection(LOOPBACK, port, timeout=5)
        try:
            connection.request(
                "POST",
                "/api/auth/login",
                body=json.dumps({"username": "sec003.nobody", "password": "irrelevant"}),
                headers={"Content-Type": "application/json", "X-Forwarded-For": FORGED_IP},
            )
            assert connection.getresponse().status == 401
        finally:
            connection.close()

    log = log_path.read_text()
    events = [
        json.loads(line.partition("patchpoint.security ")[2])
        for line in log.splitlines()
        if "patchpoint.security " in line
    ]
    assert [(event["event"], event["client_ip"]) for event in events] == [
        ("login_failed", LOOPBACK)
    ]
    assert FORGED_IP not in log
