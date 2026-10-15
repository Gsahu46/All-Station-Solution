package com.safarbus.bookings;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;

/** The booking code before the fix, kept only in tests: auto-commit on, so every statement commits by itself. */
final class OldBookingStore {

    private OldBookingStore() {
    }

    /** afterBooking runs between the two inserts: the moment a crash or a timeout would hit. */
    static long save(DataSource dataSource, Trip trip, String phone, List<Passenger> passengers, Runnable afterBooking) throws SQLException {
        try (Connection c = dataSource.getConnection()) {
            long bookingId;
            try (PreparedStatement s = c.prepareStatement("INSERT INTO bookings (trip_id, contact_phone, total_paise) VALUES (?, ?, ?)", new String[]{"id"})) {
                s.setLong(1, trip.id());
                s.setString(2, phone);
                s.setLong(3, trip.farePaise() * passengers.size());
                s.executeUpdate();   // committed now
                try (ResultSet keys = s.getGeneratedKeys()) {
                    keys.next();
                    bookingId = keys.getLong(1);
                }
            }
            afterBooking.run();
            for (Passenger p : passengers) {
                try (PreparedStatement s = c.prepareStatement(
                        "INSERT INTO booking_passengers (booking_id, trip_id, seat_no, name, age, fare_paise) VALUES (?, ?, ?, ?, ?, ?)")) {
                    s.setLong(1, bookingId);
                    s.setLong(2, trip.id());
                    s.setInt(3, p.seatNo());
                    s.setString(4, p.name());
                    s.setInt(5, p.age());
                    s.setLong(6, trip.farePaise());
                    s.executeUpdate();   // each passenger committed on its own
                }
            }
            return bookingId;
        }
    }
}
