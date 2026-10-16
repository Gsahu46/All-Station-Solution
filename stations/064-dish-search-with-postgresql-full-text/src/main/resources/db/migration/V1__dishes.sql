CREATE TABLE dishes (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city        VARCHAR(30)  NOT NULL CONSTRAINT dishes_city_shape CHECK (city ~ '^[a-z-]{3,30}$'),
    restaurant  VARCHAR(100) NOT NULL,
    name        VARCHAR(100) NOT NULL CONSTRAINT dishes_name_not_blank CHECK (btrim(name) <> ''),
    description VARCHAR(500),
    price_paise INTEGER      NOT NULL CONSTRAINT dishes_price_range CHECK (price_paise BETWEEN 1000 AND 500000),
    -- Kept by PostgreSQL itself: the words of the name (weight A) and the description (weight B), stemmed in English.
    search      TSVECTOR GENERATED ALWAYS AS (
                    setweight(to_tsvector('english', name), 'A') || setweight(to_tsvector('english', coalesce(description, '')), 'B')) STORED
);
