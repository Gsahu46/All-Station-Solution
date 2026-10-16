package com.tiffino.dishes;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules as PostgreSQL enforces them, with plain SQL, in a test city removed afterwards. */
class DishDatabaseTest extends ApiTest {

    @AfterEach
    void removeTestDishes() {
        jdbc.sql("DELETE FROM dishes WHERE city = 'testville'").update();
    }

    private long dish(String name, int paise) {
        return jdbc.sql("INSERT INTO dishes (city, restaurant, name, price_paise) VALUES ('testville', 'Test Kitchen', ?, ?) RETURNING id")
                .params(name, paise).query(Long.class).single();
    }

    private long matches(String q) {
        return jdbc.sql("SELECT count(*) FROM dishes WHERE city = 'testville' AND search @@ websearch_to_tsquery('english', ?)").param(q).query(Long.class).single();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        assertThatThrownBy(() -> dish("   ", 10000)).isInstanceOf(DataAccessException.class).hasMessageContaining("dishes_name_not_blank");
        assertThatThrownBy(() -> dish("Free Lunch", 0)).hasMessageContaining("dishes_price_range");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO dishes (city, restaurant, name, price_paise) VALUES ('Testville', 'X', 'Y', 10000)").update())
                .hasMessageContaining("dishes_city_shape");
    }

    @Test
    void theSearchColumnIsKeptByTheDatabaseNotByTheApp() {
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO dishes (city, restaurant, name, price_paise, search) VALUES ('testville', 'X', 'Y', 10000, to_tsvector('cheat'))").update())
                .rootCause().hasMessageContaining("cannot insert a non-DEFAULT value into column \"search\"");
        long id = dish("Veg Pulao", 15000);
        assertThat(matches("pulao")).isEqualTo(1);
        jdbc.sql("UPDATE dishes SET name = 'Veg Khichdi' WHERE id = ?").param(id).update();
        assertThat(matches("pulao")).isZero();   // renamed: the old word is gone from the index too
        assertThat(matches("khichdi")).isEqualTo(1);
    }

    @Test
    void aMenuWithOneBadPriceIsNotAddedAtAll() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(tx -> {
            dish("Rajma Chawal", 16000);
            dish("Chole Bhature", 18000);
            dish("Lassi", 999999);
        })).hasMessageContaining("dishes_price_range");
        assertThat(matches("rajma or chole")).isZero();
    }
}
