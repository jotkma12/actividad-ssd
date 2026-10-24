ALTER TABLE reservations RENAME TO reservations_previous;

CREATE TABLE reservations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    space_id INTEGER NOT NULL REFERENCES spaces(id) ON DELETE RESTRICT,
    starts_at_utc TEXT NOT NULL,
    ends_at_utc TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'approved', 'rejected', 'rejected_expired', 'cancelled', 'finished')
    ),
    created_at_utc TEXT NOT NULL,
    cancellation_reason TEXT,
    CHECK (starts_at_utc < ends_at_utc)
);

INSERT INTO reservations (
    id, user_id, space_id, starts_at_utc, ends_at_utc, status,
    created_at_utc, cancellation_reason
)
SELECT id, user_id, space_id, starts_at_utc, ends_at_utc, status,
       created_at_utc, cancellation_reason
FROM reservations_previous;

DROP TABLE reservations_previous;

CREATE INDEX reservations_space_interval_idx
    ON reservations (space_id, starts_at_utc, ends_at_utc);
CREATE INDEX reservations_user_idx ON reservations (user_id);

CREATE TABLE reservation_change_requests (
    id INTEGER PRIMARY KEY,
    reservation_id INTEGER NOT NULL REFERENCES reservations(id) ON DELETE RESTRICT,
    starts_at_utc TEXT NOT NULL,
    ends_at_utc TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
    reason TEXT,
    created_at_utc TEXT NOT NULL,
    resolved_at_utc TEXT,
    CHECK (starts_at_utc < ends_at_utc)
);

CREATE UNIQUE INDEX reservation_change_one_pending_idx
    ON reservation_change_requests (reservation_id)
    WHERE status = 'pending';
CREATE INDEX reservation_change_interval_idx
    ON reservation_change_requests (starts_at_utc, ends_at_utc, status);
