package com.tiffino.dishes;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
class DishSearch {

    record Dish(long id, String name, String restaurant, int pricePaise) {
    }

    record Results(String q, String city, List<Dish> dishes) {
    }

    /**
     * websearch_to_tsquery reads what people type ("paneer tikka", "\"masala dosa\" -mysore") and never fails on
     * odd characters. The query matches the stored tsvector through the GIN index; ts_rank puts name matches
     * (weight A) above description matches (weight B).
     */
    static final String SQL = """
            SELECT id, name, restaurant, price_paise
            FROM dishes, websearch_to_tsquery('english', :q) AS query
            WHERE city = :city AND search @@ query
            ORDER BY ts_rank(search, query) DESC, id
            LIMIT 20""";

    private final JdbcClient jdbc;

    DishSearch(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    Results search(String q, String city) {
        return new Results(q, city, jdbc.sql(SQL).param("q", q).param("city", city).query(Dish.class).list());
    }
}
