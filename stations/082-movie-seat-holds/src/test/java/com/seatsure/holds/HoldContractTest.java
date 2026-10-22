package com.seatsure.holds;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class HoldContractTest extends ApiTest {

    @Test
    void namedSeatsAreHeldForTenMinutes() throws Exception {
        hold("meera", "F12", "F13").andExpect(status().isCreated()).andExpect(header().string("Location", matchesPattern("/holds/[0-9a-f-]{36}")))
                .andExpect(jsonPath("$.seatNos", contains("F12", "F13"))).andExpect(jsonPath("$.totalPaise").value(70000))
                .andExpect(jsonPath("$.expiresAt").value("2026-10-30T12:10:00Z")).andExpect(jsonPath("$.status").value("held"));
    }

    @Test
    void anyTwoSeatsCanBeAskedFor() throws Exception {
        holdRequest("{\"customer\":\"arjun\",\"count\":2}").andExpect(status().isCreated()).andExpect(jsonPath("$.seatNos", contains("E10", "E11")));
    }

    @Test
    void confirmingBooksTheSeatsAndASecondConfirmAnswersTheSame() throws Exception {
        String id = holdId("meera", "F12");
        confirm(id).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("confirmed")).andExpect(jsonPath("$.paymentRef").value(matchesPattern("pay_[0-9a-f]{8}")));
        confirm(id).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("confirmed"));
        org.assertj.core.api.Assertions.assertThat(jdbc.sql("SELECT booked_by FROM seats WHERE seat_no = 'F12'").query(String.class).single()).isEqualTo("meera");
    }

    @Test
    void aTakenSeatIs409AndNamesIt() throws Exception {
        hold("meera", "F12");
        hold("arjun", "F11", "F12").andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("Taken: F12"));
        hold("arjun", "F11").andExpect(status().isCreated());   // all or none: F11 was not held by the refused request
    }

    @Test
    void anExpiredHoldCannotBeConfirmedAndTheSeatIsFreeAgain() throws Exception {
        String id = holdId("meera", "F12");
        later(Duration.ofMinutes(10));
        confirm(id).andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("This hold has expired"));
        hold("arjun", "F12").andExpect(status().isCreated());
    }

    @Test
    void unknownThingsAre404AndBadBodiesAre400() throws Exception {
        hold("meera", "Z99").andExpect(status().isNotFound());
        confirm("00000000-0000-0000-0000-000000000000").andExpect(status().isNotFound());
        holdRequest("{\"customer\":\"meera\"}").andExpect(status().isBadRequest());
        holdRequest("{\"customer\":\"meera\",\"seats\":[\"F12\"],\"count\":1}").andExpect(status().isBadRequest());
        hold("meera", "f12").andExpect(status().isBadRequest());
        hold("meera", "E10", "E11", "E12", "E13", "E14", "F10", "F11").andExpect(status().isBadRequest());
        confirm("not-a-uuid").andExpect(status().isBadRequest());
    }
}
