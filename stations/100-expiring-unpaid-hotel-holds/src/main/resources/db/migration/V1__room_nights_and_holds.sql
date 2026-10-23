-- Rooms of one type on one night: how many there are, how many are held. The rule "never more held than there are"
-- is here, for every writer, not only in Java.
CREATE TABLE room_nights (
    room_type_id bigint NOT NULL,
    stay_date    date   NOT NULL,
    total        int    NOT NULL,
    held         int    NOT NULL DEFAULT 0,
    CONSTRAINT room_nights_pk PRIMARY KEY (room_type_id, stay_date),
    CONSTRAINT room_nights_held_range CHECK (held BETWEEN 0 AND total)
);

-- One hold: one room for one night, while the guest pays (demo rule: one night per hold).
CREATE TABLE holds (
    id              bigserial   PRIMARY KEY,
    idempotency_key text        NOT NULL,
    request_hash    text        NOT NULL,
    room_type_id    bigint      NOT NULL,
    stay_date       date        NOT NULL,
    guest_email     text        NOT NULL,
    status          text        NOT NULL DEFAULT 'HELD',
    created_at      timestamptz NOT NULL,
    expires_at      timestamptz NOT NULL,
    expired_at      timestamptz,
    CONSTRAINT holds_key_once UNIQUE (idempotency_key),
    CONSTRAINT holds_status CHECK (status IN ('HELD', 'EXPIRED')),
    CONSTRAINT holds_expires_after_creation CHECK (expires_at > created_at),
    CONSTRAINT holds_expired_has_time CHECK ((status = 'EXPIRED') = (expired_at IS NOT NULL)),
    CONSTRAINT holds_room_night FOREIGN KEY (room_type_id, stay_date) REFERENCES room_nights
);
CREATE INDEX holds_due ON holds (expires_at) WHERE status = 'HELD';
