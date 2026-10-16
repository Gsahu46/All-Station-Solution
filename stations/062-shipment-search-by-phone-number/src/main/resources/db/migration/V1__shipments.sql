CREATE TABLE shipments (
    id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    awb       VARCHAR(12) NOT NULL CONSTRAINT shipments_awb_unique UNIQUE
                                   CONSTRAINT shipments_awb_shape CHECK (awb ~ '^DR[0-9]{10}$'),
    -- Stored as 10 digits only, so a search compares the column itself and can use an index.
    phone     VARCHAR(10) NOT NULL CONSTRAINT shipments_phone_shape CHECK (phone ~ '^[6-9][0-9]{9}$'),
    booked_on DATE        NOT NULL,
    status    VARCHAR(20) NOT NULL CONSTRAINT shipments_status_known CHECK (status IN ('BOOKED', 'IN_TRANSIT', 'DELIVERED', 'RETURNED'))
);
