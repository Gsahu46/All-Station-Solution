package com.tiffino.restaurants;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataAccessException;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules as PostgreSQL enforces them, with plain SQL, in a city of its own that is removed afterwards. */
class RestaurantDatabaseTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    @BeforeEach
    void testCity() {
        jdbc.sql("INSERT INTO cities (code, name) VALUES ('testville', 'Testville')").update();
    }

    @AfterEach
    void removeTestCity() {
        jdbc.sql("DELETE FROM restaurants WHERE city_code = 'testville'").update();   // cascades to its cuisines and reviews
        jdbc.sql("DELETE FROM cities WHERE code = 'testville'").update();
    }

    private long restaurant(String name) {
        return jdbc.sql("INSERT INTO restaurants (city_code, name) VALUES ('testville', ?) RETURNING id").param(name).query(Long.class).single();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        long id = restaurant("Test Dhaba");
        jdbc.sql("INSERT INTO restaurant_cuisines VALUES (?, 1)").param(id).update();
        assertThatThrownBy(() -> restaurant("Test Dhaba")).isInstanceOf(DataAccessException.class).hasMessageContaining("restaurants_name_per_city");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO restaurant_cuisines VALUES (?, 1)").param(id).update()).hasMessageContaining("restaurant_cuisines_pk");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO restaurant_cuisines VALUES (?, 99)").param(id).update()).hasMessageContaining("restaurant_cuisines_cuisine_fk");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO reviews (restaurant_id, rating) VALUES (?, 6)").param(id).update()).hasMessageContaining("reviews_rating_range");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO restaurants (city_code, name) VALUES ('jaipur', 'X')").update()).hasMessageContaining("restaurants_city_fk");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO cities (code, name) VALUES ('Jaipur', 'Jaipur')").update()).hasMessageContaining("cities_code_shape");
    }

    @Test
    void aRestaurantWithABadCuisineIsNotAddedAtAll() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(status -> {
            long id = restaurant("Half Added");
            jdbc.sql("INSERT INTO restaurant_cuisines VALUES (?, 1)").param(id).update();
            jdbc.sql("INSERT INTO restaurant_cuisines VALUES (?, 99)").param(id).update();
        })).hasMessageContaining("restaurant_cuisines_cuisine_fk");
        assertThat(jdbc.sql("SELECT count(*) FROM restaurants WHERE name = 'Half Added'").query(Long.class).single()).isZero();
    }

    @Test
    void removingARestaurantRemovesItsCuisinesAndReviews() {
        long id = restaurant("Closing Down");
        jdbc.sql("INSERT INTO restaurant_cuisines VALUES (?, 2)").param(id).update();
        jdbc.sql("INSERT INTO reviews (restaurant_id, rating) VALUES (?, 4)").param(id).update();
        jdbc.sql("DELETE FROM restaurants WHERE id = ?").param(id).update();
        assertThat(jdbc.sql("SELECT count(*) FROM restaurant_cuisines WHERE restaurant_id = ?").param(id).query(Long.class).single()).isZero();
        assertThat(jdbc.sql("SELECT count(*) FROM reviews WHERE restaurant_id = ?").param(id).query(Long.class).single()).isZero();
    }
}
