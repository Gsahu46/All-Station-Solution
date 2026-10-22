CREATE TABLE shows (
    id        bigint CONSTRAINT shows_pk PRIMARY KEY,
    title     text NOT NULL,
    starts_at timestamptz NOT NULL
);

-- One row per seat per show: the row lock on it is the lock on the seat.
CREATE TABLE seats (
    show_id     bigint NOT NULL CONSTRAINT seats_show_fk REFERENCES shows,
    seat_no     text NOT NULL,
    price_paise bigint NOT NULL,
    hold_id     uuid,
    held_until  timestamptz,
    booked_by   text,
    CONSTRAINT seats_pk PRIMARY KEY (show_id, seat_no),
    CONSTRAINT seats_no_shape CHECK (seat_no ~ '^[A-Z][0-9]{1,2}$'),
    CONSTRAINT seats_price_positive CHECK (price_paise > 0),
    -- A hold has both an id and an end; a booked seat is not also held.
    CONSTRAINT seats_hold_complete CHECK ((hold_id IS NULL) = (held_until IS NULL)),
    CONSTRAINT seats_booked_not_held CHECK (booked_by IS NULL OR hold_id IS NULL)
);

CREATE TABLE holds (
    id          uuid CONSTRAINT holds_pk PRIMARY KEY,
    show_id     bigint NOT NULL CONSTRAINT holds_show_fk REFERENCES shows,
    customer    text NOT NULL,
    seat_nos    text[] NOT NULL,
    total_paise bigint NOT NULL,
    expires_at  timestamptz NOT NULL,
    status      text NOT NULL,
    payment_ref text,
    CONSTRAINT holds_status CHECK (status IN ('held', 'confirmed', 'refunded')),
    CONSTRAINT holds_total_positive CHECK (total_paise > 0),
    CONSTRAINT holds_some_seats CHECK (cardinality(seat_nos) BETWEEN 1 AND 6),
    CONSTRAINT holds_confirmed_paid CHECK (status = 'held' OR payment_ref IS NOT NULL)
);
