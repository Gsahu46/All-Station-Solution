CREATE TABLE amenities (
    code VARCHAR(20) PRIMARY KEY CONSTRAINT amenities_code_shape CHECK (code ~ '^[a-z]{2,20}$'),
    name VARCHAR(50) NOT NULL
);

CREATE TABLE hotels (
    id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                  VARCHAR(100) NOT NULL,
    city                  VARCHAR(30)  NOT NULL CONSTRAINT hotels_city_shape CHECK (city ~ '^[a-z-]{3,30}$'),
    stars                 SMALLINT     NOT NULL CONSTRAINT hotels_stars_range CHECK (stars BETWEEN 1 AND 5),
    price_per_night_paise BIGINT       NOT NULL CONSTRAINT hotels_price_range CHECK (price_per_night_paise BETWEEN 50000 AND 10000000),
    CONSTRAINT hotels_name_per_city UNIQUE (city, name)
);
CREATE INDEX hotels_city_price ON hotels (city, price_per_night_paise);

CREATE TABLE hotel_amenities (
    hotel_id     BIGINT      NOT NULL CONSTRAINT hotel_amenities_hotel_fk REFERENCES hotels (id) ON DELETE CASCADE,
    amenity_code VARCHAR(20) NOT NULL CONSTRAINT hotel_amenities_amenity_fk REFERENCES amenities (code),
    CONSTRAINT hotel_amenities_pk PRIMARY KEY (hotel_id, amenity_code)
);
CREATE INDEX hotel_amenities_amenity ON hotel_amenities (amenity_code, hotel_id);
