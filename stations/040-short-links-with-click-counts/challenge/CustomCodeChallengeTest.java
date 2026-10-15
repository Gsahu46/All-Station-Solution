package com.chhotu.links;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: marketing may ask for a code of its own ("Diwali7"), seven base62 characters. If it is taken, that is
 * a 409: a chosen code is never swapped for a random one, and never takes over the existing link.
 */
class CustomCodeChallengeTest extends ApiTest {

    ResultActions createWithCode(String url, String code) throws Exception {
        return mvc.perform(post("/links").contentType(MediaType.APPLICATION_JSON)
                .content("{\"targetUrl\":\"%s\",\"code\":\"%s\"}".formatted(url, code)));
    }

    @Test
    void aFreeCustomCodeIsUsedAsGiven() throws Exception {
        createWithCode("https://shop.example/diwali", "Diwali7").andExpect(status().isCreated()).andExpect(jsonPath("$.code").value("Diwali7"));
        follow("Diwali7").andExpect(status().isFound());
    }

    @Test
    void aTakenCustomCodeIs409AndTheOldLinkStays() throws Exception {
        createWithCode("https://shop.example/diwali", "Diwali7").andExpect(status().isCreated());
        createWithCode("https://other.example/", "Diwali7").andExpect(status().isConflict());
        assertThat(targetOf("Diwali7")).isEqualTo("https://shop.example/diwali");
        createWithCode("https://shop.example/x", "diwali-7").andExpect(status().isBadRequest());
    }
}
