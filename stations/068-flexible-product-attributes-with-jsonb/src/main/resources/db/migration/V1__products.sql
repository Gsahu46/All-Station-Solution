CREATE TABLE sellers (
    id   BIGINT       PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE categories (
    code VARCHAR(30) PRIMARY KEY,
    name VARCHAR(60) NOT NULL
);

-- What each category's attributes may be. Read by the app to validate; data, not code, so a new category needs no release.
CREATE TABLE attribute_definitions (
    category_code VARCHAR(30) NOT NULL CONSTRAINT attribute_definitions_category_fk REFERENCES categories (code),
    name          VARCHAR(30) NOT NULL CONSTRAINT attribute_definitions_name_shape CHECK (name ~ '^[a-z][a-z_]{1,29}$'),
    required      BOOLEAN     NOT NULL,
    allowed       TEXT[],      -- null: any text up to 40 characters
    CONSTRAINT attribute_definitions_pk PRIMARY KEY (category_code, name)
);

-- Fields every product has, that need a rule or a join, are columns. Only what differs per category is jsonb.
CREATE TABLE products (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku           VARCHAR(30)  NOT NULL CONSTRAINT products_sku_unique UNIQUE,
    name          VARCHAR(120) NOT NULL,
    category_code VARCHAR(30)  NOT NULL CONSTRAINT products_category_fk REFERENCES categories (code),
    seller_id     BIGINT       NOT NULL CONSTRAINT products_seller_fk REFERENCES sellers (id),
    price_paise   INTEGER      NOT NULL CONSTRAINT products_price_range CHECK (price_paise BETWEEN 100 AND 10000000),
    attributes    JSONB        NOT NULL CONSTRAINT products_attributes_object CHECK (jsonb_typeof(attributes) = 'object')
);
-- jsonb_path_ops: a smaller GIN index that answers containment (@>) only, which is the one question asked here.
CREATE INDEX products_attributes ON products USING GIN (attributes jsonb_path_ops);
CREATE INDEX products_category ON products (category_code);
