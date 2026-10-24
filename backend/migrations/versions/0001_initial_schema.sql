CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL CHECK (length(trim(full_name)) > 0),
    institutional_email TEXT NOT NULL UNIQUE CHECK (length(trim(institutional_email)) > 0),
    identification TEXT NOT NULL UNIQUE CHECK (length(trim(identification)) > 0),
    password_hash TEXT NOT NULL CHECK (length(password_hash) > 0),
    role TEXT NOT NULL CHECK (role IN ('administrator', 'requester', 'approver')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at_utc TEXT NOT NULL
);

CREATE TABLE spaces (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    type TEXT NOT NULL CHECK (length(trim(type)) > 0),
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    location TEXT NOT NULL CHECK (length(trim(location)) > 0),
    equipment_json TEXT NOT NULL DEFAULT '[]',
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    requires_approval INTEGER NOT NULL CHECK (requires_approval IN (0, 1)),
    created_at_utc TEXT NOT NULL
);

CREATE TABLE reservations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    space_id INTEGER NOT NULL REFERENCES spaces(id) ON DELETE RESTRICT,
    starts_at_utc TEXT NOT NULL,
    ends_at_utc TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'approved', 'rejected', 'cancelled', 'finished')
    ),
    created_at_utc TEXT NOT NULL,
    CHECK (starts_at_utc < ends_at_utc)
);

CREATE INDEX reservations_space_interval_idx
    ON reservations (space_id, starts_at_utc, ends_at_utc);
CREATE INDEX reservations_user_idx ON reservations (user_id);

CREATE TABLE maintenance_blocks (
    id INTEGER PRIMARY KEY,
    space_id INTEGER NOT NULL REFERENCES spaces(id) ON DELETE RESTRICT,
    starts_at_utc TEXT NOT NULL,
    ends_at_utc TEXT NOT NULL,
    reason TEXT NOT NULL CHECK (length(trim(reason)) > 0),
    created_at_utc TEXT NOT NULL,
    CHECK (starts_at_utc < ends_at_utc)
);

CREATE INDEX maintenance_blocks_space_interval_idx
    ON maintenance_blocks (space_id, starts_at_utc, ends_at_utc);

CREATE TABLE history_events (
    id INTEGER PRIMARY KEY,
    actor_user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
    occurred_at_utc TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK (length(trim(entity_type)) > 0),
    entity_id INTEGER NOT NULL,
    action TEXT NOT NULL CHECK (length(trim(action)) > 0),
    old_values_json TEXT,
    new_values_json TEXT,
    reason TEXT
);

CREATE INDEX history_events_entity_idx
    ON history_events (entity_type, entity_id, occurred_at_utc, id);
