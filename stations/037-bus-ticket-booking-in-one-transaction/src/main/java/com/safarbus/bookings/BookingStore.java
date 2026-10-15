package com.safarbus.bookings;

import org.springframework.stereotype.Repository;

import javax.sql.DataSource;
import java.sql.Array;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

/**
 * Saves a booking and its passengers as one unit. Auto-commit is switched off, so the booking row and every passenger
 * row become visible together at commit, or, after any failure, not at all.
 */
@Repository
class BookingStore {

    private final DataSource dataSource;

    BookingStore(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    long save(Trip trip, String phone, List<Passenger> passengers) throws SQLException {
        try (Connection c = dataSource.getConnection()) {
            c.setAutoCommit(false);
            try {
                long bookingId = insertBooking(c, trip, phone, trip.farePaise() * passengers.size());
                insertPassengers(c, bookingId, trip, passengers);
                c.commit();
                return bookingId;
            } catch (SQLException | RuntimeException e) {
                c.rollback();   // the booking row goes too: nothing half-saved
                throw e;
            } finally {
                c.setAutoCommit(true);   // the pool lends this connection out again next
            }
        }
    }

    /** The database creates the id; RETURN_GENERATED_KEYS for the "id" column hands it back. */
    private static long insertBooking(Connection c, Trip trip, String phone, long totalPaise) throws SQLException {
        try (PreparedStatement s = c.prepareStatement(
                "INSERT INTO bookings (trip_id, contact_phone, total_paise) VALUES (?, ?, ?)", new String[]{"id"})) {
            s.setLong(1, trip.id());
            s.setString(2, phone);
            s.setLong(3, totalPaise);
            s.executeUpdate();
            try (ResultSet keys = s.getGeneratedKeys()) {
                keys.next();
                return keys.getLong(1);
            }
        }
    }

    /** One statement, one row per passenger, sent to the database as a batch: one round trip, not six. */
    private static void insertPassengers(Connection c, long bookingId, Trip trip, List<Passenger> passengers) throws SQLException {
        try (PreparedStatement s = c.prepareStatement(
                "INSERT INTO booking_passengers (booking_id, trip_id, seat_no, name, age, fare_paise) VALUES (?, ?, ?, ?, ?, ?)")) {
            for (Passenger p : passengers) {
                s.setLong(1, bookingId);
                s.setLong(2, trip.id());
                s.setInt(3, p.seatNo());
                s.setString(4, p.name().strip());
                s.setInt(5, p.age());
                s.setLong(6, trip.farePaise());
                s.addBatch();
            }
            s.executeBatch();
        }
    }

    /** Which of these seats are already booked on the trip. */
    List<Integer> taken(long tripId, List<Integer> seats) throws SQLException {
        try (Connection c = dataSource.getConnection();
             PreparedStatement s = c.prepareStatement("SELECT seat_no FROM booking_passengers WHERE trip_id = ? AND seat_no = ANY (?) ORDER BY seat_no")) {
            Array array = c.createArrayOf("integer", seats.toArray());
            s.setLong(1, tripId);
            s.setArray(2, array);
            try (ResultSet r = s.executeQuery()) {
                List<Integer> found = new ArrayList<>();
                while (r.next()) {
                    found.add(r.getInt(1));
                }
                return found;
            }
        }
    }

    /** A unique violation (SQLState 23505) of this constraint. PostgreSQL's driver puts both on the batch's own exception. */
    static boolean violates(SQLException e, String constraint) {
        return "23505".equals(e.getSQLState()) && String.valueOf(e.getMessage()).contains(constraint);
    }
}
