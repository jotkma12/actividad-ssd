CREATE TABLE users_new (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL CHECK (length(trim(full_name)) > 0),
    institutional_email TEXT NOT NULL UNIQUE CHECK (length(trim(institutional_email)) > 0),
    identification TEXT UNIQUE CHECK (identification IS NULL OR length(trim(identification)) > 0),
    password_hash TEXT NOT NULL CHECK (length(password_hash) > 0),
    role TEXT NOT NULL CHECK (role IN ('administrator', 'requester', 'approver')),
    is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
    created_at_utc TEXT NOT NULL
);

INSERT INTO users_new (
    id, full_name, institutional_email, identification, password_hash,
    role, is_active, created_at_utc
)
SELECT
    id, full_name, institutional_email, identification, password_hash,
    role, is_active, created_at_utc
FROM users;

DROP TABLE users;
ALTER TABLE users_new RENAME TO users;

CREATE TABLE user_sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at_utc TEXT NOT NULL
);

CREATE INDEX user_sessions_user_idx ON user_sessions (user_id);

CREATE TABLE space_approvers (
    space_id INTEGER NOT NULL REFERENCES spaces(id) ON DELETE RESTRICT,
    approver_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    assigned_at_utc TEXT NOT NULL,
    PRIMARY KEY (space_id, approver_user_id)
);
