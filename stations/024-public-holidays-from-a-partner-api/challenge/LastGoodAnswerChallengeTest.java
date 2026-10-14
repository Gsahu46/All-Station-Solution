package com.teamdesk.holidays;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: a year's holidays rarely change. Keep the last good answer per year and state, and serve it when
 * the provider fails or is too slow. The response says where it came from: "provider" or "cache".
 */
class LastGoodAnswerChallengeTest extends ApiTest {

    @Test
    void aFailingProviderIsCoveredByTheLastGoodAnswer() throws Exception {
        holidays("2027", "MH").andExpect(status().isOk()).andExpect(jsonPath("$.source").value("provider"));
        STUB.behaviour = StubProvider.Behaviour.FAIL;
        holidays("2027", "MH").andExpect(status().isOk()).andExpect(jsonPath("$.source").value("cache"))
                .andExpect(jsonPath("$.holidays[0].name").value("Republic Day"));
        STUB.behaviour = StubProvider.Behaviour.SLOW;
        holidays("2027", "MH").andExpect(status().isOk()).andExpect(jsonPath("$.source").value("cache"));
    }

    @Test
    void withNothingCachedTheFailureStillShows() throws Exception {
        STUB.behaviour = StubProvider.Behaviour.FAIL;
        holidays("2028", "MH").andExpect(status().isBadGateway());
    }
}
