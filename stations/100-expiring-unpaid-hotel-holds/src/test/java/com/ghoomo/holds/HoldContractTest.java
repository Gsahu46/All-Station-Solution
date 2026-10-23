package com.ghoomo.holds;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class HoldContractTest extends ApiTest {

    @Test
    void aHoldTakesARoomForFifteenMinutesThenExpires() throws Exception {
        hold("first-hold-01", 2, "2026-12-31", "Asha@Example.com").andExpect(status().isCreated())
                .andExpect(header().string("Location", "/holds/1"))
                .andExpect(jsonPath("$.id").value(1)).andExpect(jsonPath("$.roomTypeId").value(2))
                .andExpect(jsonPath("$.date").value("2026-12-31")).andExpect(jsonPath("$.status").value("HELD"))
                .andExpect(jsonPath("$.expiresAt").value("2026-12-20T10:15:00Z"))
                .andExpect(jsonPath("$.guestEmail").doesNotExist());
        hold("second-hold-1", 2, "2026-12-31", "ravi@example.com").andExpect(status().isConflict());   // the one suite is taken

        CLOCK.advance(Duration.ofMinutes(15));
        org.assertj.core.api.Assertions.assertThat(holds.expireDue()).isEqualTo(1);
        mvc.perform(get("/holds/1")).andExpect(status().isOk()).andExpect(jsonPath("$.status").value("EXPIRED"));
        hold("second-hold-1", 2, "2026-12-31", "ravi@example.com").andExpect(status().isCreated());   // free again
    }

    @Test
    void aHoldBeforeItsTimeIsNotExpired() throws Exception {
        hold("first-hold-01", 1, "2026-12-25", "asha@example.com").andExpect(status().isCreated());
        CLOCK.advance(Duration.ofMinutes(14).plusSeconds(59));
        org.assertj.core.api.Assertions.assertThat(holds.expireDue()).isZero();
        mvc.perform(get("/holds/1")).andExpect(jsonPath("$.status").value("HELD"));
    }

    @Test
    void badRequestsAre400AndUnknownThings404() throws Exception {
        hold(null, 1, "2026-12-25", "asha@example.com").andExpect(status().isBadRequest());   // no Idempotency-Key
        hold("short", 1, "2026-12-25", "asha@example.com").andExpect(status().isBadRequest());
        hold("good-key-0001", 1, "25-12-2026", "asha@example.com").andExpect(status().isBadRequest());
        hold("good-key-0001", 1, "2026-12-25", "not-an-email").andExpect(status().isBadRequest());
        hold("good-key-0001", 0, "2026-12-25", "asha@example.com").andExpect(status().isBadRequest());
        hold("good-key-0001", 1, "2027-01-15", "asha@example.com").andExpect(status().isNotFound());   // no such night
        hold("good-key-0001", 9, "2026-12-25", "asha@example.com").andExpect(status().isNotFound());
        mvc.perform(get("/holds/999")).andExpect(status().isNotFound());
        mvc.perform(get("/holds/abc")).andExpect(status().isBadRequest());
        org.assertj.core.api.Assertions.assertThat(held(1, "2026-12-25")).isZero();
    }
}
