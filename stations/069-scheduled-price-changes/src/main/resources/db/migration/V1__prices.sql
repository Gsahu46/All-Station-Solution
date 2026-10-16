CREATE EXTENSION IF NOT EXISTS btree_gist;   -- lets a GiST exclusion constraint compare product_id with =

CREATE TABLE products (
    id   BIGINT       PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- Every price a product has had or will have, each valid for a half-open stretch of time [valid_from, valid_to).
-- valid_to NULL means "until further notice". Nothing is overwritten, so "what did it cost at 21:04 yesterday" has an answer.
CREATE TABLE prices (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id  BIGINT      NOT NULL CONSTRAINT prices_product_fk REFERENCES products (id),
    price_paise INTEGER     NOT NULL CONSTRAINT prices_price_range CHECK (price_paise BETWEEN 100 AND 10000000),
    valid_from  TIMESTAMPTZ NOT NULL,
    valid_to    TIMESTAMPTZ,
    CONSTRAINT prices_window_order CHECK (valid_to IS NULL OR valid_to > valid_from),
    -- At any instant, at most one price per product: checkout can never find two.
    CONSTRAINT prices_no_overlap EXCLUDE USING gist (product_id WITH =, tstzrange(valid_from, valid_to, '[)') WITH &&)
);
