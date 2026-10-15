package com.safarbus.bookings;

import org.junit.jupiter.api.Test;

import java.sql.SQLException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The first test written for this station: the old code's half-saved bookings, on the real database. */
class AutoCommitTrapTest extends ApiTest {

    @Test
    void aCrashAfterTheBookingRowLeavesABookingWithNoPassengers() throws Exception {
        assertThatThrownBy(() -> OldBookingStore.save(dataSource, trip101(), "9876543210", seats(4, 5),
                () -> { throw new IllegalStateException("crash between the two inserts"); }))
                .hasMessage("crash between the two inserts");
        assertThat(bookingsWithoutPassengers()).isEqualTo(1);
    }

    @Test
    void aTakenSeatHalfwayLeavesHalfABooking() throws Exception {
        store.save(trip101(), "9876543210", seats(5));
        assertThatThrownBy(() -> OldBookingStore.save(dataSource, trip101(), "9123456780", seats(4, 5), () -> { }))
                .isInstanceOf(SQLException.class);
        // The second booking exists, charged for two seats, with seat 4 only.
        assertThat(bookings()).isEqualTo(2);
        assertThat(jdbc.sql("SELECT count(*) FROM booking_passengers WHERE booking_id = 2").query(Long.class).single()).isEqualTo(1);
    }

    @Test
    void inOneTransactionTheSameFailureLeavesNothing() throws Exception {
        store.save(trip101(), "9876543210", seats(5));
        assertThatThrownBy(() -> store.save(trip101(), "9123456780", seats(4, 5))).isInstanceOf(SQLException.class);
        assertThat(bookings()).isEqualTo(1);
        assertThat(passengers()).isEqualTo(1);
        assertThat(bookingsWithoutPassengers()).isZero();
    }
}
