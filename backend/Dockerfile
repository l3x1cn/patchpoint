# Obraz API PatchPoint (Faza 3): multi-stage, okrojony obraz bazowy python:3.14.10-slim (Debian),
# proces bez uprawnień roota (UID 10001), bez pip i bez narzędzi budowania. Kontekst to katalog backend/:
#   make images  (docker build -t patchpoint-api:local backend)
# Obrazy bazowe są przypięte po digeście; podbija je Dependabot (.github/dependabot.yml).

FROM ghcr.io/astral-sh/uv:0.13.10@sha256:a3ea1357342c1a4bf9a0c53a3deb1b55379aefa037338d8113d5771efa01774f AS uv

FROM python:3.14.10-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /src
# Tylko zależności produkcyjne z uv.lock; --locked przerywa budowę, gdy lock nie pasuje do pyproject.toml.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

FROM python:3.14.10-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f
# Poprawki bezpieczeństwa Debiana, których obraz bazowy jeszcze nie ma, i obraz bez pip: zależności
# instaluje uv w etapie build. Pakiety Debiana zależą więc od dnia budowy; digest bazy zostaje przypięty.
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get upgrade --yes \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall --yes --root-user-action=ignore pip
ENV PATH=/app/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATCHPOINT_DATABASE_PATH=/data/patchpoint.db
COPY --from=build /app/.venv /app/.venv
# Tryb nie zależy od umask i uprawnień checkoutu: kod jest czytelny dla UID 10001, ale niezapisywalny.
# chmod zamiast symbolicznego COPY --chmod: starszy BuildKit (Docker 28 na runnerze CI) odbiera podkatalogom bit x.
COPY app /app/app
# /data to punkt montowania wolumenu z bazą SQLite; nowy wolumen dziedziczy właściciela katalogu z obrazu.
RUN chmod -R u=rwX,go=rX /app/app && mkdir /data && chown 10001:10001 /data
WORKDIR /app
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --start-interval=2s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"]
# X-Forwarded-For jest przyjmowany tylko od adresów z FORWARDED_ALLOW_IPS (bez zmiennej: 127.0.0.1 i ::1);
# compose.yaml wpisuje tam wyłącznie adres reverse proxy.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
