package com.safarbus.bookings;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: passengers aged 60 or more pay 75% of the fare (demo rule), rounded to the nearest paisa, half up.
 * Each passenger row stores its own fare, and the booking's total is exactly the sum of them.
 */
class SeniorFareChallengeTest extends ApiTest {

    @Test
    void seniorsPayThreeQuartersAndTheTotalIsTheSumOfTheRows() throws Exception {
        book("""
                {"tripId":101,"contactPhone":"9876543210","passengers":[
                  {"name":"Asha Verma","age":34,"seatNo":12},{"name":"Kamala Verma","age":65,"seatNo":13}]}""")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.totalPaise").value(125_000 + 93_750));
        assertThat(jdbc.sql("SELECT fare_paise FROM booking_passengers ORDER BY seat_no").query(Long.class).list()).containsExactly(125_000L, 93_750L);
        assertThat(jdbc.sql("SELECT b.total_paise = (SELECT sum(fare_paise) FROM booking_passengers p WHERE p.booking_id = b.id) FROM bookings b")
                .query(Boolean.class).single()).isTrue();
    }

    @Test
    void halfAPaisaRoundsUp() throws Exception {
        jdbc.sql("UPDATE trips SET fare_paise = 85_001 WHERE id = 102").update();   // 75% is 63,750.75
        try {
            book("""
                    {"tripId":102,"contactPhone":"9876543210","passengers":[{"name":"Old","age":60,"seatNo":1}]}""")
                    .andExpect(jsonPath("$.totalPaise").value(63_751));
        } finally {
            jdbc.sql("UPDATE trips SET fare_paise = 85000 WHERE id = 102").update();
        }
    }
}
