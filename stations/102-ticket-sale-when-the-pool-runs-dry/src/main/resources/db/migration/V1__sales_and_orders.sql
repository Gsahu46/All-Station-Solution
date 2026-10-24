-- A sale: seats to sell and how many are taken. "Never more taken than there are" is checked here too.
CREATE TABLE sales (
    id          bigint PRIMARY KEY,
    name        text   NOT NULL,
    capacity    int    NOT NULL,
    sold        int    NOT NULL DEFAULT 0,
    price_paise bigint NOT NULL,
    CONSTRAINT sales_sold_range CHECK (sold BETWEEN 0 AND capacity),
    CONSTRAINT sales_price_positive CHECK (price_paise > 0)
);

CREATE TABLE orders (
    id           bigserial   PRIMARY KEY,
    sale_id      bigint      NOT NULL REFERENCES sales,
    buyer        text        NOT NULL,
    seats        int         NOT NULL,
    amount_paise bigint      NOT NULL,
    status       text        NOT NULL,
    charge_id    text,
    created_at   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT orders_seats_range CHECK (seats BETWEEN 1 AND 6),
    CONSTRAINT orders_amount_positive CHECK (amount_paise > 0),
    CONSTRAINT orders_status CHECK (status IN ('PENDING_PAYMENT', 'PAID', 'FAILED')),
    CONSTRAINT orders_paid_has_charge CHECK ((status = 'PAID') = (charge_id IS NOT NULL))
);
