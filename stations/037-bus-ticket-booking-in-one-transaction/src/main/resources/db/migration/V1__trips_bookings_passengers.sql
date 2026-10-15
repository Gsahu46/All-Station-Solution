CREATE TABLE trips (
    id          BIGINT       PRIMARY KEY,
    route       VARCHAR(100) NOT NULL,
    departs_at  TIMESTAMPTZ  NOT NULL,
    seats       SMALLINT     NOT NULL,
    fare_paise  BIGINT       NOT NULL,
    CONSTRAINT trips_seats_range   CHECK (seats BETWEEN 1 AND 60),
    CONSTRAINT trips_fare_positive CHECK (fare_paise > 0)
);

CREATE TABLE bookings (
    id            BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trip_id       BIGINT      NOT NULL,
    contact_phone CHAR(10)    NOT NULL,
    total_paise   BIGINT      NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT bookings_trip_fk        FOREIGN KEY (trip_id) REFERENCES trips (id),
    CONSTRAINT bookings_phone_digits   CHECK (contact_phone ~ '^[6-9][0-9]{9}$'),
    CONSTRAINT bookings_total_positive CHECK (total_paise > 0),
    -- Lets passengers reference (booking, trip) together, so a passenger's trip is always its booking's trip.
    CONSTRAINT bookings_id_trip_unique UNIQUE (id, trip_id)
);

-- A booking with no passengers cannot be stopped by a CHECK on one row: the transaction is what prevents it.
CREATE TABLE booking_passengers (
    booking_id BIGINT       NOT NULL,
    trip_id    BIGINT       NOT NULL,
    seat_no    SMALLINT     NOT NULL,
    name       VARCHAR(60)  NOT NULL,
    age        SMALLINT     NOT NULL,
    fare_paise BIGINT       NOT NULL,
    PRIMARY KEY (booking_id, seat_no),
    CONSTRAINT booking_passengers_booking_fk FOREIGN KEY (booking_id, trip_id) REFERENCES bookings (id, trip_id),
    CONSTRAINT booking_passengers_seat_once  UNIQUE (trip_id, seat_no),
    CONSTRAINT booking_passengers_seat_range CHECK (seat_no BETWEEN 1 AND 60),
    CONSTRAINT booking_passengers_age_range  CHECK (age BETWEEN 0 AND 120),
    CONSTRAINT booking_passengers_fare_positive CHECK (fare_paise > 0)
);
