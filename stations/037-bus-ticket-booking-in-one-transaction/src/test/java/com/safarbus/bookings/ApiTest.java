package com.safarbus.bookings;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import javax.sql.DataSource;
import java.util.List;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the app with a real PostgreSQL, no bookings before each test. Trips 101 (40 seats) and 102 exist. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    DataSource dataSource;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    Trips trips;
    @Autowired
    BookingStore store;

    @BeforeEach
    void noBookings() {
        jdbc.sql("TRUNCATE booking_passengers, bookings RESTART IDENTITY").update();
    }

    ResultActions book(String json) throws Exception {
        return mvc.perform(post("/bookings").contentType(MediaType.APPLICATION_JSON).content(json));
    }

    long bookings() {
        return jdbc.sql("SELECT count(*) FROM bookings").query(Long.class).single();
    }

    long passengers() {
        return jdbc.sql("SELECT count(*) FROM booking_passengers").query(Long.class).single();
    }

    long bookingsWithoutPassengers() {
        return jdbc.sql("SELECT count(*) FROM bookings b WHERE NOT EXISTS (SELECT 1 FROM booking_passengers p WHERE p.booking_id = b.id)")
                .query(Long.class).single();
    }

    Trip trip101() throws Exception {
        return trips.find(101).orElseThrow();
    }

    static List<Passenger> seats(int... seatNos) {
        return java.util.Arrays.stream(seatNos).mapToObj(n -> new Passenger("Passenger " + n, 30, n)).toList();
    }
}
