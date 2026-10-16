CREATE TABLE cities (
    code VARCHAR(30)  PRIMARY KEY CONSTRAINT cities_code_shape CHECK (code ~ '^[a-z-]{3,30}$'),
    name VARCHAR(100) NOT NULL
);

CREATE TABLE cuisines (
    id   BIGINT       PRIMARY KEY,
    name VARCHAR(50)  NOT NULL CONSTRAINT cuisines_name_unique UNIQUE
);

CREATE TABLE restaurants (
    id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_code VARCHAR(30)  NOT NULL CONSTRAINT restaurants_city_fk REFERENCES cities (code),
    name      VARCHAR(100) NOT NULL,
    CONSTRAINT restaurants_name_per_city UNIQUE (city_code, name)
);
-- The home screen's query: restaurants of one city in name order.
CREATE INDEX restaurants_city_name ON restaurants (city_code, name, id);

CREATE TABLE restaurant_cuisines (
    restaurant_id BIGINT NOT NULL CONSTRAINT restaurant_cuisines_restaurant_fk REFERENCES restaurants (id) ON DELETE CASCADE,
    cuisine_id    BIGINT NOT NULL CONSTRAINT restaurant_cuisines_cuisine_fk REFERENCES cuisines (id),
    CONSTRAINT restaurant_cuisines_pk PRIMARY KEY (restaurant_id, cuisine_id)
);

CREATE TABLE reviews (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    restaurant_id BIGINT   NOT NULL CONSTRAINT reviews_restaurant_fk REFERENCES restaurants (id) ON DELETE CASCADE,
    rating        SMALLINT NOT NULL CONSTRAINT reviews_rating_range CHECK (rating BETWEEN 1 AND 5)
);
CREATE INDEX reviews_restaurant ON reviews (restaurant_id);
