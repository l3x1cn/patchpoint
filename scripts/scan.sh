#!/usr/bin/env bash
# Bramki skanerów bezpieczeństwa PatchPoint, te same lokalnie (make semgrep, make trivy-fs,
# make trivy-images) i w CI (.github/workflows/ci.yml):
#   scripts/scan.sh semgrep               SAST (Semgrep CE, zestawy reguł z rejestru); kod 1 przy znalezisku
#   scripts/scan.sh fs                    Trivy na drzewie repozytorium: podatności zależności (backend/uv.lock),
#                                         sekrety i konfiguracja Dockerfile; kod 1 przy HIGH lub CRITICAL
#   scripts/scan.sh image <nazwa> <obraz> Trivy na obrazie z lokalnego Dockera; kod 1 przy HIGH lub CRITICAL
#                                         z dostępną poprawką
# Skanery działają z obrazów przypiętych po digeście: bez instalacji i bez aquasecurity/trivy-action
# (CVE-2026-33634). Pełne wyniki (wszystkie poziomy): reports/<nazwa>.json i reports/<nazwa>.sarif.
# Wyjątki: .semgrepignore (ścieżki), komentarz nosemgrep z identyfikatorem reguły i uzasadnieniem,
# .trivyignore (zasady w pliku). Kod 2: złe argumenty.
set -euo pipefail

cd "$(dirname "$0")/.."

SEMGREP_IMAGE="semgrep/semgrep:1.185.0@sha256:67518c174185a2043fdbed16c70631b79209499b3671178e7194379b48295a0d"
TRIVY_IMAGE="aquasec/trivy:0.76.2@sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb"
SEMGREP_CONFIGS=(p/python p/javascript p/dockerfile p/docker-compose p/github-actions p/owasp-top-ten)
TRIVY_SKIP_DIRS=".git,.av,reports,backend/.venv,backend/.mypy_cache,backend/.pytest_cache,backend/.ruff_cache,deploy/proxy/dev-tls,deploy/ansible/.ansible"

REPORTS="$PWD/reports"
TRIVY_CACHE="${TRIVY_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/patchpoint-trivy}"
USER_SPEC="$(id -u):$(id -g)"

usage() {
  echo "Użycie: $0 semgrep | fs | image <nazwa> <obraz>" >&2
  exit 2
}

# trivy_run [argumenty docker run ...] -- <argumenty trivy ...>
trivy_run() {
  local docker_args=()
  while [[ $# -gt 0 && "$1" != "--" ]]; do
    docker_args+=("$1")
    shift
  done
  shift
  docker run --rm --user "$USER_SPEC" -e HOME=/tmp \
    -v "$PWD:/src:ro" -v "$REPORTS:/reports" -v "$TRIVY_CACHE:/cache" -w /src \
    "${docker_args[@]}" "$TRIVY_IMAGE" --cache-dir /cache --quiet "$@"
}

# trivy_gate <nazwa> <skanery> — SARIF z pełnego wyniku i bramka HIGH/CRITICAL (tabela tego, co blokuje)
trivy_gate() {
  local name="$1" scanners="$2"
  trivy_run -- convert --format sarif --output "/reports/$name.sarif" "/reports/$name.json"
  if trivy_run -- convert --scanners "$scanners" --severity HIGH,CRITICAL --exit-code 1 --format table "/reports/$name.json"; then
    echo "Bramka Trivy ($name): brak znalezisk HIGH i CRITICAL. Wyniki: reports/$name.json, reports/$name.sarif"
  else
    echo "Bramka Trivy ($name): znaleziska HIGH lub CRITICAL (tabela wyżej). Wyniki: reports/$name.json, reports/$name.sarif" >&2
    exit 1
  fi
}

case "${1:-}" in
  semgrep)
    [[ $# -eq 1 ]] || usage
    mkdir -p "$REPORTS"
    rm -f "$REPORTS/semgrep.json" "$REPORTS/semgrep.sarif"
    configs=()
    for config in "${SEMGREP_CONFIGS[@]}"; do
      configs+=(--config "$config")
    done
    set +e
    docker run --rm --user "$USER_SPEC" -e HOME=/tmp -e SEMGREP_SEND_METRICS=off \
      -v "$PWD:/src:ro" -v "$REPORTS:/reports" -w /src "$SEMGREP_IMAGE" \
      semgrep scan --metrics=off --error "${configs[@]}" \
      --json-output=/reports/semgrep.json --sarif-output=/reports/semgrep.sarif .
    status=$?
    set -e
    case "$status" in
      0) echo "Bramka Semgrep: brak znalezisk. Wyniki: reports/semgrep.json, reports/semgrep.sarif" ;;
      1)
        echo "Bramka Semgrep: znaleziska (lista wyżej). Wyniki: reports/semgrep.json, reports/semgrep.sarif" >&2
        exit 1
        ;;
      *)
        echo "Semgrep zakończył się błędem (kod $status)." >&2
        exit "$status"
        ;;
    esac
    ;;
  fs)
    [[ $# -eq 1 ]] || usage
    mkdir -p "$REPORTS" "$TRIVY_CACHE"
    rm -f "$REPORTS/trivy-fs.json" "$REPORTS/trivy-fs.sarif"
    trivy_run -- fs --scanners vuln,secret,misconfig --ignore-unfixed --ignorefile /src/.trivyignore \
      --skip-dirs "$TRIVY_SKIP_DIRS" --format json --output /reports/trivy-fs.json /src
    trivy_gate trivy-fs vuln,secret,misconfig
    ;;
  image)
    [[ $# -eq 3 ]] || usage
    name="trivy-image-$2"
    mkdir -p "$REPORTS" "$TRIVY_CACHE"
    rm -f "$REPORTS/$name.json" "$REPORTS/$name.sarif"
    work="$(mktemp -d)"
    trap 'rm -rf "$work"' EXIT
    docker save "$3" -o "$work/image.tar"
    trivy_run -v "$work:/work:ro" -- image --scanners vuln --ignore-unfixed --ignorefile /src/.trivyignore \
      --input /work/image.tar --format json --output "/reports/$name.json"
    trivy_gate "$name" vuln
    ;;
  *)
    usage
    ;;
esac
