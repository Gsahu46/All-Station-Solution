package com.teamdesk.holidays;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Every other way the provider fails, and that its error text never reaches our clients. */
class ProviderFailureTest extends ApiTest {

    /** A year per failure, never fetched successfully, so no earlier answer can stand in for the failure. */
    String bodyFor(StubProvider.Behaviour behaviour, int expectedStatus, String expectedTitle) throws Exception {
        STUB.behaviour = behaviour;
        return holidays(String.valueOf(2040 + behaviour.ordinal()), "KA").andExpect(status().is(expectedStatus)).andExpect(jsonPath("$.title").value(expectedTitle))
                .andReturn().getResponse().getContentAsString();
    }

    @Test
    void aProvider500IsOur502WithoutTheirInternals() throws Exception {
        assertThat(bodyFor(StubProvider.Behaviour.FAIL, 502, "Holiday provider failed")).doesNotContain("db-holidays").doesNotContain("5432");
    }

    @Test
    void ourExpiredKeyIsOur502NotTheClients401() throws Exception {
        assertThat(bodyFor(StubProvider.Behaviour.BAD_KEY, 502, "Holiday provider failed")).doesNotContain("tdk_live");
    }

    @Test
    void anAnswerWeCannotReadIs502() throws Exception {
        bodyFor(StubProvider.Behaviour.BAD_JSON, 502, "Holiday provider failed");
    }

    @Test
    void aDroppedConnectionIs502NotATimeout() throws Exception {
        bodyFor(StubProvider.Behaviour.HANG_UP, 502, "Holiday provider unreachable");
    }
}
