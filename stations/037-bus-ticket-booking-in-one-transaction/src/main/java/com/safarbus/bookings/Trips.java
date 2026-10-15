package com.safarbus.bookings;

import org.springframework.stereotype.Repository;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Optional;

@Repository
class Trips {

    private final DataSource dataSource;

    Trips(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    Optional<Trip> find(long id) throws SQLException {
        try (Connection c = dataSource.getConnection();
             PreparedStatement s = c.prepareStatement("SELECT id, route, seats, fare_paise FROM trips WHERE id = ?")) {
            s.setLong(1, id);
            try (ResultSet r = s.executeQuery()) {
                return r.next() ? Optional.of(new Trip(r.getLong("id"), r.getString("route"), r.getInt("seats"), r.getLong("fare_paise"))) : Optional.empty();
            }
        }
    }
}
