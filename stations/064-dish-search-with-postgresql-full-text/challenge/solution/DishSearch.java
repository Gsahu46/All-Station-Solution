package com.tiffino.dishes;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
class DishSearch {

    record Dish(long id, String name, String restaurant, int pricePaise) {
    }

    record Results(String q, String city, List<Dish> dishes, List<String> suggestions) {
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

    /** Challenge 1: the same search with a budget. */
    static final String WITHIN_BUDGET = SQL.replace("AND search @@ query", "AND search @@ query AND price_paise <= :maxPaise");

    private final JdbcClient jdbc;

    DishSearch(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    Results search(String q, String city) {
        return search(q, city, Integer.MAX_VALUE);
    }

    /** Challenge 1: a budget; challenge 2: suggestions only when full-text found nothing. */
    Results search(String q, String city, int maxPaise) {
        List<Dish> dishes = jdbc.sql(WITHIN_BUDGET).param("q", q).param("city", city).param("maxPaise", maxPaise).query(Dish.class).list();
        List<String> suggestions = dishes.isEmpty() ? jdbc.sql("""
                        SELECT name FROM dishes WHERE city = :city AND lower(name) % lower(:q)
                        GROUP BY name ORDER BY max(similarity(lower(name), lower(:q))) DESC, name LIMIT 5""")
                .param("city", city).param("q", q).query(String.class).list() : List.of();
        return new Results(q, city, dishes, suggestions);
    }
}
