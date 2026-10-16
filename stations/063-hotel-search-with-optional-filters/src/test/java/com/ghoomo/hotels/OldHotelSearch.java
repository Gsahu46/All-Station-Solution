package com.ghoomo.hotels;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.util.List;

/** The search as it was, kept in the tests only: optional filters glued into one SQL string. */
@Component
class OldHotelSearch {

    private final JdbcTemplate jdbc;

    OldHotelSearch(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    List<String> search(String city, Long minPrice, List<String> amenities, String sort) {
        String sql = "SELECT h.name FROM hotels h";
        if (!amenities.isEmpty()) {
            sql += " JOIN hotel_amenities a ON a.hotel_id = h.id";
        }
        sql += " WHERE 1=1";
        if (city != null) {
            sql += " AND h.city = '" + city + "'";
        }
        if (minPrice != null) {
            sql += " AND h.price_per_night_paise >= " + minPrice * 100;
        }
        if (!amenities.isEmpty()) {
            sql += " AND a.amenity_code IN ('" + String.join("', '", amenities) + "')";
        }
        sql += " ORDER BY " + sort + " LIMIT 20";
        return jdbc.queryForList(sql, String.class);
    }
}
