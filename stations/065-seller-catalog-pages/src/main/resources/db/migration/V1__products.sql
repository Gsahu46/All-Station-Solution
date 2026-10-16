CREATE TABLE sellers (
    id   BIGINT       PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE products (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    seller_id   BIGINT       NOT NULL CONSTRAINT products_seller_fk REFERENCES sellers (id),
    name        VARCHAR(120) NOT NULL CONSTRAINT products_name_not_blank CHECK (btrim(name) <> ''),
    price_paise INTEGER      NOT NULL CONSTRAINT products_price_range CHECK (price_paise BETWEEN 100 AND 10000000),
    created_on  DATE         NOT NULL,
    CONSTRAINT products_name_per_seller UNIQUE (seller_id, name)
);
-- One index per allowed sort, each ending in id: the order the page query asks for, already sorted.
CREATE INDEX products_seller_price ON products (seller_id, price_paise, id);
CREATE INDEX products_seller_created ON products (seller_id, created_on, id);
-- (seller_id, name) is already indexed by products_name_per_seller, and names are unique per seller.
