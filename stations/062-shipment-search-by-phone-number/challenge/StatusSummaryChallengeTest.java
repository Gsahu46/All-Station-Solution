package com.dakroute.shipments;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /shipments/summary?phone&from&to counts a phone's shipments per status, e.g. {"DELIVERED": 2}.
 * The busy seller asks for whole months, so the count must be answered from the index alone: an Index Only Scan,
 * never a visit to the table rows.
 */
class StatusSummaryChallengeTest extends ApiTest {

    @Test
    void countsPerStatus() throws Exception {
        mvc.perform(get("/shipments/summary").param("phone", "+91 98765 43210").param("from", "2026-01-01").param("to", "2026-12-31")).andExpect(status().isOk())
                .andExpect(jsonPath("$.DELIVERED").value(1)).andExpect(jsonPath("$.RETURNED").value(1)).andExpect(jsonPath("$.IN_TRANSIT").value(1));
    }

    @Test
    void theSellersMonthIsCountedFromTheIndexAlone() {
        jdbc.sql("VACUUM shipments").update();   // marks pages all-visible, which an index-only scan relies on
        Plan plan = explain("SELECT status, count(*) FROM shipments WHERE phone = :phone AND booked_on BETWEEN :from AND :to GROUP BY status",
                SELLER, LocalDate.of(2026, 3, 1), LocalDate.of(2026, 3, 31));
        assertThat(plan.nodes()).contains("Index Only Scan");
    }
}
