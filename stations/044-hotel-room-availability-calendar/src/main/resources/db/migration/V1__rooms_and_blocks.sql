CREATE TABLE rooms (
    id       BIGINT       PRIMARY KEY,
    hotel    VARCHAR(80)  NOT NULL,
    name     VARCHAR(80)  NOT NULL,
    capacity SMALLINT     NOT NULL,
    CONSTRAINT rooms_capacity_range CHECK (capacity BETWEEN 1 AND 10)
);

-- A block holds a room for the nights from check_in up to, but not including, check_out: the half-open range
-- [check_in, check_out). 10 to 12 June is the nights of the 10th and 11th; the next guest may check in on the 12th.
CREATE TABLE room_blocks (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    room_id    BIGINT      NOT NULL,
    check_in   DATE        NOT NULL,
    check_out  DATE        NOT NULL,
    guest_name VARCHAR(80) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT room_blocks_room_fk     FOREIGN KEY (room_id) REFERENCES rooms (id),
    CONSTRAINT room_blocks_dates_order CHECK (check_out > check_in)
);

-- The guarantee, for every writer and every race: no two blocks of one room share a night. '[)' is half-open, the
-- same rule as the Java check, so back-to-back stays (out on the 12th, in on the 12th) are allowed.
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE room_blocks ADD CONSTRAINT room_blocks_no_overlap
    EXCLUDE USING gist (room_id WITH =, daterange(check_in, check_out, '[)') WITH &&);
