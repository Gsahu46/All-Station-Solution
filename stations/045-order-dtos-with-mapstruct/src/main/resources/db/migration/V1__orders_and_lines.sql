CREATE TABLE orders (
    id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name         VARCHAR(80)  NOT NULL,
    phone                 VARCHAR(10)  NOT NULL,
    address_line          VARCHAR(200) NOT NULL,
    city                  VARCHAR(40)  NOT NULL,
    pincode               VARCHAR(6)   NOT NULL,
    delivery_instructions VARCHAR(200),             -- added in March; the hand-written mapper never learned about it
    status                VARCHAR(12)  NOT NULL,
    total_paise           BIGINT       NOT NULL,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT orders_phone_digits    CHECK (phone ~ '^[6-9][0-9]{9}$'),
    CONSTRAINT orders_pincode_digits  CHECK (pincode ~ '^[1-9][0-9]{5}$'),
    CONSTRAINT orders_status_known    CHECK (status IN ('PLACED', 'COOKING', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED')),
    CONSTRAINT orders_total_positive  CHECK (total_paise > 0)
);

CREATE TABLE order_lines (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id         BIGINT      NOT NULL,
    item             VARCHAR(80) NOT NULL,
    quantity         INT         NOT NULL,
    unit_price_paise BIGINT      NOT NULL,
    CONSTRAINT order_lines_order_fk         FOREIGN KEY (order_id) REFERENCES orders (id),
    CONSTRAINT order_lines_quantity_range   CHECK (quantity BETWEEN 1 AND 20),
    CONSTRAINT order_lines_price_positive   CHECK (unit_price_paise > 0)
);
