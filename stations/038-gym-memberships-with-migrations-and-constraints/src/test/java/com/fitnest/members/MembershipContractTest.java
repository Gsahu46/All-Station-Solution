package com.fitnest.members;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.json.JsonCompareMode;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: members and memberships, and every refusal. */
class MembershipContractTest extends ApiTest {

    @Test
    void aNewMemberGetsAnIdAndOneStoredPhoneForm() throws Exception {
        join("Asha Verma", "+91 98765-43210").andExpect(status().isCreated())
                .andExpect(content().json("""
                        {"id":1,"name":"Asha Verma","phone":"9876543210"}""", JsonCompareMode.STRICT));
    }

    @Test
    void theSamePhoneInAnotherFormatIs409() throws Exception {
        join("Asha Verma", "9876543210").andExpect(status().isCreated());
        join("Asha V", "098765 43210").andExpect(status().isConflict())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Phone already registered"));
        assertThat(count("members")).isEqualTo(1);
    }

    @Test
    void aMembershipRunsToTheDayBeforeTheSameDateNextPeriod() throws Exception {
        join("Asha Verma", "9876543210");
        buy(1, "quarterly", "2026-11-15").andExpect(status().isCreated())
                .andExpect(content().json("""
                        {"id":1,"memberId":1,"planCode":"QUARTERLY","startsOn":"2026-11-15","endsOn":"2027-02-14","pricePaise":399900}""", JsonCompareMode.LENIENT));   // every field checked; later fields may be added
        buy(1, "MONTHLY", "2027-01-31").andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Overlapping membership"));
        buy(1, "MONTHLY", "2027-02-15").andExpect(status().isCreated()).andExpect(jsonPath("$.endsOn").value("2027-03-14"));
    }

    @Test
    void unknownMembersAre404AndUnknownPlans422() throws Exception {
        buy(99, "MONTHLY", "2026-11-01").andExpect(status().isNotFound());
        join("Asha Verma", "9876543210");
        buy(1, "WEEKLY", "2026-11-01").andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Unknown plan"));
    }

    @Test
    void badRequestsAre400() throws Exception {
        join("Asha Verma", "12345").andExpect(status().isBadRequest());
        join("", "9876543210").andExpect(status().isBadRequest());
        join("Asha Verma", "9876543210");
        buy(1, "MONTHLY", "2026-02-30").andExpect(status().isBadRequest());
        buy(1, "", "2026-11-01").andExpect(status().isBadRequest());
        assertThat(count("memberships")).isZero();
    }
}
