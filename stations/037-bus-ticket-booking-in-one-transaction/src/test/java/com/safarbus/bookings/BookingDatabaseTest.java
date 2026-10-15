package com.safarbus.bookings;

import com.zaxxer.hikari.HikariDataSource;
import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The database's rules with Java bypassed, and what commit, rollback and a dead connection do. */
class BookingDatabaseTest extends ApiTest {

    void sql(Connection c, String sql) throws SQLException {
        try (PreparedStatement s = c.prepareStatement(sql)) {
            s.executeUpdate();
        }
    }

    @Test
    void namedConstraintsHoldWithoutJava() throws SQLException {
        try (Connection c = dataSource.getConnection()) {
            sql(c, "INSERT INTO bookings (trip_id, contact_phone, total_paise) VALUES (101, '9876543210', 125000)");   // booking 1
            sql(c, "INSERT INTO booking_passengers VALUES (1, 101, 7, 'A', 30, 125000)");
            assertThatThrownBy(() -> sql(c, "INSERT INTO bookings (trip_id, contact_phone, total_paise) VALUES (101, '12345', 125000)"))
                    .hasMessageContaining("bookings_phone_digits");
            assertThatThrownBy(() -> sql(c, "INSERT INTO booking_passengers VALUES (1, 101, 8, 'B', 130, 125000)"))
                    .hasMessageContaining("booking_passengers_age_range");
            assertThatThrownBy(() -> sql(c, "INSERT INTO booking_passengers VALUES (1, 102, 9, 'C', 30, 125000)"))
                    .hasMessageContaining("booking_passengers_booking_fk");   // a passenger on another trip than its booking
        }
    }

    @Test
    void oneSeatOnOneTripBelongsToOneBookingOnly() throws Exception {
        store.save(trip101(), "9876543210", seats(7));
        try (Connection c = dataSource.getConnection()) {
            sql(c, "INSERT INTO bookings (trip_id, contact_phone, total_paise) VALUES (101, '9123456780', 125000)");   // booking 2
            assertThatThrownBy(() -> sql(c, "INSERT INTO booking_passengers VALUES (2, 101, 7, 'B', 30, 125000)"))
                    .hasMessageContaining("booking_passengers_seat_once");
        }
    }

    @Test
    void aDeadConnectionCommitsNothing() throws SQLException {
        HikariDataSource pool = (HikariDataSource) dataSource;   // a connection of its own, outside the pool, to kill
        Connection c = DriverManager.getConnection(pool.getJdbcUrl(), pool.getUsername(), pool.getPassword());
        c.setAutoCommit(false);
        sql(c, "INSERT INTO bookings (trip_id, contact_phone, total_paise) VALUES (101, '9876543210', 125000)");
        c.abort(Runnable::run);   // the process dies before commit: the server rolls the transaction back
        assertThat(bookings()).isZero();
    }

    @Test
    void aRefusedPassengerRollsBackTheWholeBooking() throws Exception {
        List<Passenger> oneTooOld = List.of(new Passenger("Fine", 30, 1), new Passenger("Refused by the database", 130, 2));
        assertThatThrownBy(() -> store.save(trip101(), "9876543210", oneTooOld)).hasMessageContaining("booking_passengers_age_range");
        assertThat(bookings()).isZero();
        assertThat(passengers()).isZero();
    }

    @Test
    void aJavaErrorMidwayRollsBackToo() throws Exception {
        // A passenger with no name fails in Java (strip() on null) after the booking row is inserted. Without the
        // rollback, the finally block's setAutoCommit(true) would commit that booking: JDBC commits on that call.
        assertThatThrownBy(() -> store.save(trip101(), "9876543210", List.of(new Passenger(null, 30, 1))))
                .isInstanceOf(NullPointerException.class);
        assertThat(bookings()).isZero();
    }

    @Test
    void generatedIdsComeBackAndTheBatchSavesEveryRow() throws Exception {
        long first = store.save(trip101(), "9876543210", seats(1, 2, 3, 4, 5, 6));
        long second = store.save(trip101(), "9876543210", seats(7));
        assertThat(second).isEqualTo(first + 1);
        assertThat(jdbc.sql("SELECT seat_no FROM booking_passengers WHERE booking_id = ? ORDER BY seat_no").param(first).query(Integer.class).list())
                .containsExactly(1, 2, 3, 4, 5, 6);
    }
}
