package com.teamdesk.holidays;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: the provider wants an API key in an X-Api-Key header. The key comes from configuration
 * (teamdesk.holidays.api-key, set from an environment variable in real life) and never appears in our responses.
 */
@TestPropertySource(properties = "teamdesk.holidays.api-key=tdk_test_1234")
class ApiKeyChallengeTest extends ApiTest {

    @Test
    void everyCallCarriesTheKeyAndNoResponseShowsIt() throws Exception {
        String body = holidays("2026", "DL").andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        assertThat(STUB.lastApiKey).isEqualTo("tdk_test_1234");
        assertThat(body).doesNotContain("tdk_test_1234");
    }
}
