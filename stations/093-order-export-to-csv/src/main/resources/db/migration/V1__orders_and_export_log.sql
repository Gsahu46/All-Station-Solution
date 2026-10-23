CREATE TABLE orders (
    id           bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT orders_pk PRIMARY KEY,
    seller_id    bigint NOT NULL,
    order_ref    text NOT NULL,
    placed_at    timestamptz NOT NULL,
    product_name text NOT NULL,
    quantity     integer NOT NULL,
    amount_paise bigint NOT NULL,
    buyer_city   text NOT NULL,
    status       text NOT NULL,
    CONSTRAINT orders_ref_once_per_seller UNIQUE (seller_id, order_ref),
    CONSTRAINT orders_quantity_positive CHECK (quantity > 0),
    CONSTRAINT orders_amount_positive CHECK (amount_paise > 0),
    CONSTRAINT orders_status CHECK (status IN ('PLACED', 'SHIPPED', 'DELIVERED', 'CANCELLED'))
);
CREATE INDEX orders_seller_time ON orders (seller_id, placed_at);

-- Every export of buyers' data is recorded before it starts: who, which days, when.
CREATE TABLE export_log (
    id          bigint GENERATED ALWAYS AS IDENTITY CONSTRAINT export_log_pk PRIMARY KEY,
    seller_id   bigint NOT NULL,
    from_date   date NOT NULL,
    to_date     date NOT NULL,
    exported_at timestamptz NOT NULL DEFAULT now(),
    -- Demo rule: at most a year per export, 366 days with both ends included.
    CONSTRAINT export_log_range CHECK (to_date >= from_date AND to_date - from_date < 366)
);
