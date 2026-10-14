package com.tijori.profiles;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the bug before the fix. */
class FullNumberTrapTest extends ApiTest {

    /** The "before" profile: plain strings. The app masked them on screen; the API sent them whole. Kept only in tests. */
    record OldProfile(String name, String aadhaar, String cardNumber) {
    }

    @Test
    void theOldResponseCarriesTheFullNumbersWhateverTheScreenShows() {
        String json = JsonMapper.builder().build().writeValueAsString(new OldProfile("Asha Rao", "234567890123", "4111111111111111"));
        assertThat(json).contains("234567890123").contains("4111111111111111");   // in every log, proxy and screenshot of the response
        assertThat(new OldProfile("Asha Rao", "234567890123", "4111111111111111").toString()).contains("234567890123");
    }

    @Test
    void theRealResponseIsMaskedBeforeItLeavesTheServer() throws Exception {
        String body = profileAs("asha", "c-1001")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.aadhaar").value("XXXX XXXX 0123"))
                .andExpect(jsonPath("$.cards[0].number").value("XXXX XXXX XXXX 1111"))
                .andReturn().getResponse().getContentAsString();
        RAW_NUMBERS.forEach(raw -> assertThat(body).doesNotContain(raw));
        assertThat(body).doesNotContainPattern("\\d{5,}");   // no run of five digits anywhere in the profile
    }

    @Test
    void anyMapperMasksBecauseTheRuleIsOnTheType() {
        // Not just Spring's configured mapper: a plain one, as someone might use for logging, masks too.
        String json = JsonMapper.builder().build().writeValueAsString(Sensitive.aadhaar("234567890123"));
        assertThat(json).isEqualTo("\"XXXX XXXX 0123\"");
    }
}
