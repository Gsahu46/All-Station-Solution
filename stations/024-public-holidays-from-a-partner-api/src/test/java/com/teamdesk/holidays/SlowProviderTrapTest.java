package com.teamdesk.holidays;

import org.junit.jupiter.api.Test;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.RestClient;

import java.time.Duration;
import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the bugs before the fix. */
class SlowProviderTrapTest extends ApiTest {

    /** The "before" call: a RestClient with no timeout and no error handling. Kept only in tests. */
    static String oldCall() {
        return RestClient.create(STUB.baseUrl()).get().uri("/v1/holidays?year=2026&region=KA").retrieve().body(String.class);
    }

    @Test
    void theOldCallWaitsAsLongAsTheProviderLikes() {
        STUB.behaviour = StubProvider.Behaviour.SLOW;
        Instant start = Instant.now();
        oldCall();
        assertThat(Duration.between(start, Instant.now())).isGreaterThanOrEqualTo(Duration.ofMillis(1_900));
        // every request thread stuck like this is one fewer for everyone else
    }

    @Test
    void theOldCallTurnsTheProvidersFailureIntoOurs() {
        STUB.behaviour = StubProvider.Behaviour.FAIL;
        assertThatThrownBy(SlowProviderTrapTest::oldCall)
                .isInstanceOf(HttpServerErrorException.InternalServerError.class);   // uncaught: our API answers 500
    }

    @Test
    void theRealEndpointGivesUpInTimeAndSaysWhoFailed() throws Exception {
        STUB.behaviour = StubProvider.Behaviour.SLOW;
        Instant start = Instant.now();
        holidays("2030", "KA").andExpect(status().isGatewayTimeout())   // years no test fetches successfully: nothing cached
                .andExpect(jsonPath("$.title").value("Holiday provider too slow"));
        assertThat(Duration.between(start, Instant.now())).isLessThan(Duration.ofMillis(1_500));

        STUB.behaviour = StubProvider.Behaviour.FAIL;
        holidays("2031", "KA").andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.title").value("Holiday provider failed"));
    }
}
