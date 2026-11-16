CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    full_name     TEXT    NOT NULL,
    department    TEXT    NOT NULL DEFAULT '',
    role          TEXT    NOT NULL DEFAULT 'employee',
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash   TEXT    PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    created_at   TEXT    NOT NULL,
    last_seen_at TEXT    NOT NULL,
    expires_at   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS login_failures (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT    NOT NULL,
    attempted_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_login_failures_username
    ON login_failures (username, attempted_at);

CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL,
    category    TEXT    NOT NULL,
    priority    TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'open',
    asset_tag   TEXT,
    location    TEXT,
    reporter_id INTEGER NOT NULL REFERENCES users(id),
    assignee_id INTEGER REFERENCES users(id),
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS comments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id  INTEGER NOT NULL REFERENCES tickets(id),
    author_id  INTEGER NOT NULL REFERENCES users(id),
    body       TEXT    NOT NULL,
    created_at TEXT    NOT NULL
);

PRAGMA user_version = 2;
