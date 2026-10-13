package com.kartwala.search;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: punctuation in names or prefixes must not stop a match. */
class PunctuationChallengeTest extends ApiTest {

    @Test
    void aSpaceMatchesAHyphen() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "parle g"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("Parle-G Biscuits")));
        mvc.perform(get("/suggestions").param("prefix", "55 inch"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("Samsung 55-inch Crystal TV")));
    }

    @Test
    void aHyphenInThePrefixStillMatches() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "Parle-G"))
                .andExpect(jsonPath("$.prefix").value("parle g"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("Parle-G Biscuits")));
    }

    @Test
    void anAmpersandIsIgnored() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "head shoulders"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("Head & Shoulders Shampoo")));
    }

    @Test
    void onlyPunctuationIsTooShort() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "--&&--")).andExpect(status().isBadRequest());
    }
}
