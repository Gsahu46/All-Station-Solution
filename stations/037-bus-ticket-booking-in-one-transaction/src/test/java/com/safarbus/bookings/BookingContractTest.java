package com.safarbus.bookings;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.json.JsonCompareMode;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: trip 101, Pune to Goa, 40 seats at ₹1,250. */
class BookingContractTest extends ApiTest {

    static final String TWO = """
            {"tripId":101,"contactPhone":"9876543210","passengers":[
              {"name":"Asha Verma","age":34,"seatNo":12},{"name":"Kabir Verma","age":8,"seatNo":13}]}""";

    @Test
    void aBookingSavesEveryPassengerAndReturnsTheNewId() throws Exception {
        book(TWO).andExpect(status().isCreated()).andExpect(content().json("""
                {"bookingId":1,"tripId":101,"seats":[12,13],"totalPaise":250000,"status":"CONFIRMED"}""", JsonCompareMode.STRICT));
        assertThat(passengers()).isEqualTo(2);
    }

    @Test
    void aTakenSeatIs409AndNothingIsSaved() throws Exception {
        book(TWO).andExpect(status().isCreated());
        book("""
                {"tripId":101,"contactPhone":"9123456780","passengers":[
                  {"name":"Ravi Iyer","age":41,"seatNo":11},{"name":"Meena Iyer","age":39,"seatNo":12}]}""")
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.detail").value("Seat 12 is already booked on trip 101. Nothing was booked."));
        assertThat(bookings()).isEqualTo(1);
        assertThat(passengers()).isEqualTo(2);
        book("""
                {"tripId":101,"contactPhone":"9123456780","passengers":[{"name":"Ravi Iyer","age":41,"seatNo":11}]}""")
                .andExpect(status().isCreated());   // seat 11 was never held by the failed attempt
    }

    @Test
    void theSameSeatOnAnotherTripIsFine() throws Exception {
        book(TWO).andExpect(status().isCreated());
        book(TWO.replace("101", "102")).andExpect(status().isCreated()).andExpect(jsonPath("$.totalPaise").value(170000));
    }

    @Test
    void anUnknownTripIs404() throws Exception {
        book(TWO.replace("101", "999")).andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
    }

    @Test
    void seatsThatCannotBeBookedAre422() throws Exception {
        book(TWO.replace("\"seatNo\":13", "\"seatNo\":41")).andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.title").value("No such seat"));
        book(TWO.replace("\"seatNo\":13", "\"seatNo\":12")).andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.title").value("Same seat twice"));
        assertThat(bookings()).isZero();
    }

    @Test
    void badBodiesAre400() throws Exception {
        book(TWO.replace("9876543210", "12345")).andExpect(status().isBadRequest());
        book(TWO.replace("\"age\":8", "\"age\":130")).andExpect(status().isBadRequest());
        book(TWO.replace("\"seatNo\":12", "\"seatNo\":0")).andExpect(status().isBadRequest());
        book("""
                {"tripId":101,"contactPhone":"9876543210","passengers":[]}""").andExpect(status().isBadRequest());
        String seven = "{\"name\":\"P\",\"age\":30,\"seatNo\":%d}";
        StringBuilder many = new StringBuilder();
        for (int i = 1; i <= 7; i++) {
            many.append(i > 1 ? "," : "").append(seven.formatted(i));
        }
        book("{\"tripId\":101,\"contactPhone\":\"9876543210\",\"passengers\":[" + many + "]}").andExpect(status().isBadRequest());
        book(TWO.replace("\"tripId\":101", "\"tripId\":101,\"totalPaise\":1")).andExpect(status().isBadRequest());
        assertThat(bookings()).isZero();
    }
}
