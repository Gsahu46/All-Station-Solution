-- Order numbers come from a database sequence: one counter for every app instance, and it survives restarts.
-- nextval() never hands the same value out twice, even to transactions running at the same moment. Values used by a
-- transaction that rolls back are not returned, so numbers can have gaps; they are labels, not a count of orders.
-- 7 digits: 1000001 to 9999999 (about 90 lakh orders). NO CYCLE: when it runs out, inserts fail loudly instead of
-- repeating old numbers.
CREATE SEQUENCE order_number_seq START WITH 1000001 MINVALUE 1000001 MAXVALUE 9999999 NO CYCLE;

CREATE TABLE orders (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,   -- internal key, never shown to customers
    order_number VARCHAR(12) NOT NULL,
    outlet_id    VARCHAR(5)  NOT NULL,
    total_paise  BIGINT      NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT orders_number_unique  UNIQUE (order_number),
    CONSTRAINT orders_number_format  CHECK (order_number ~ '^TF-[0-9]{7}-[0-9]$'),
    CONSTRAINT orders_total_positive CHECK (total_paise > 0)
);
