CREATE TABLE flash_sales (
    id          BIGINT       PRIMARY KEY,
    product     VARCHAR(80)  NOT NULL,
    stock_total INT          NOT NULL,
    stock_left  INT          NOT NULL,
    price_paise BIGINT       NOT NULL,
    starts_at   TIMESTAMPTZ  NOT NULL,
    ends_at     TIMESTAMPTZ  NOT NULL,
    -- The last line of defence: whatever the code does, stock can never go below zero or above what there was.
    CONSTRAINT flash_sales_stock_not_negative CHECK (stock_left >= 0),
    CONSTRAINT flash_sales_stock_within_total CHECK (stock_left <= stock_total),
    CONSTRAINT flash_sales_price_positive     CHECK (price_paise > 0),
    CONSTRAINT flash_sales_window_order       CHECK (ends_at > starts_at)
);

CREATE TABLE purchases (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sale_id     BIGINT      NOT NULL,
    customer_id VARCHAR(10) NOT NULL,
    price_paise BIGINT      NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT purchases_sale_fk          FOREIGN KEY (sale_id) REFERENCES flash_sales (id),
    CONSTRAINT purchases_one_per_customer UNIQUE (sale_id, customer_id)   -- demo rule: one phone per customer
);
