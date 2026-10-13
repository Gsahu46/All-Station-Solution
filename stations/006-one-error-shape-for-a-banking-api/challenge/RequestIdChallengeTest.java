package com.tijori.beneficiaries;

import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: every response carries a request id, and every problem body repeats it, so support can find the log lines. */
class RequestIdChallengeTest extends ApiTest {

    @Test
    void aValidRequestIdFromTheAppIsKeptInTheHeaderAndTheProblem() throws Exception {
        mvc.perform(get("/beneficiaries/{id}", UUID.randomUUID()).with(httpBasic("asha", "asha-demo-pass"))
                        .header("X-Request-Id", "app-7f3c9a2e-0001"))
                .andExpect(status().isNotFound())
                .andExpect(header().string("X-Request-Id", "app-7f3c9a2e-0001"))
                .andExpect(jsonPath("$.requestId").value("app-7f3c9a2e-0001"));
    }

    @Test
    void anUnsafeRequestIdIsReplacedNotEchoed() throws Exception {
        mvc.perform(get("/beneficiaries/{id}", UUID.randomUUID()).with(httpBasic("asha", "asha-demo-pass"))
                        .header("X-Request-Id", "<script>x</script>"))
                .andExpect(header().string("X-Request-Id", matchesPattern("[0-9a-f-]{36}")))
                .andExpect(jsonPath("$.requestId", matchesPattern("[0-9a-f-]{36}")));
    }

    @Test
    void securityErrorsCarryItToo() throws Exception {
        mvc.perform(get("/beneficiaries/{id}", UUID.randomUUID()).header("X-Request-Id", "app-7f3c9a2e-0002"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.requestId").value("app-7f3c9a2e-0002"));
    }
}
