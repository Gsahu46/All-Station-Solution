package com.ghoomo.hotels;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataAccessException;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules as PostgreSQL enforces them, with plain SQL; test hotels are in "testville" and removed afterwards. */
class HotelDatabaseTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    @AfterEach
    void removeTestHotels() {
        jdbc.sql("DELETE FROM hotels WHERE city = 'testville'").update();
    }

    private long hotel(String name, String city, int stars, long paise) {
        return jdbc.sql("INSERT INTO hotels (name, city, stars, price_per_night_paise) VALUES (?, ?, ?, ?) RETURNING id")
                .params(name, city, stars, paise).query(Long.class).single();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        long id = hotel("Test Inn", "testville", 3, 300000);
        assertThatThrownBy(() -> hotel("Test Inn", "testville", 4, 400000)).isInstanceOf(DataAccessException.class).hasMessageContaining("hotels_name_per_city");
        assertThatThrownBy(() -> hotel("Six Stars", "testville", 6, 400000)).hasMessageContaining("hotels_stars_range");
        assertThatThrownBy(() -> hotel("Free Stay", "testville", 3, 0)).hasMessageContaining("hotels_price_range");
        assertThatThrownBy(() -> hotel("Shouting", "TESTVILLE", 3, 300000)).hasMessageContaining("hotels_city_shape");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO hotel_amenities VALUES (?, 'sauna')").param(id).update()).hasMessageContaining("hotel_amenities_amenity_fk");
        jdbc.sql("INSERT INTO hotel_amenities VALUES (?, 'wifi')").param(id).update();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO hotel_amenities VALUES (?, 'wifi')").param(id).update()).hasMessageContaining("hotel_amenities_pk");
    }

    @Test
    void aHotelWithAnUnknownAmenityIsNotAddedAtAll() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(tx -> {
            long id = hotel("Half Listed", "testville", 3, 300000);
            jdbc.sql("INSERT INTO hotel_amenities VALUES (?, 'wifi')").param(id).update();
            jdbc.sql("INSERT INTO hotel_amenities VALUES (?, 'sauna')").param(id).update();
        })).hasMessageContaining("hotel_amenities_amenity_fk");
        assertThat(jdbc.sql("SELECT count(*) FROM hotels WHERE name = 'Half Listed'").query(Long.class).single()).isZero();
    }

    @Test
    void removingAHotelRemovesItsAmenities() {
        long id = hotel("Closing Inn", "testville", 2, 150000);
        jdbc.sql("INSERT INTO hotel_amenities VALUES (?, 'parking')").param(id).update();
        jdbc.sql("DELETE FROM hotels WHERE id = ?").param(id).update();
        assertThat(jdbc.sql("SELECT count(*) FROM hotel_amenities WHERE hotel_id = ?").param(id).query(Long.class).single()).isZero();
    }
}
