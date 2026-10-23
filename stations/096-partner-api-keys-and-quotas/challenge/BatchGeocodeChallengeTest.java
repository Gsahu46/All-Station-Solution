package com.mapwise.geocode;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: POST /geocode/batch looks up 1 to 10 addresses at once. It costs one request per address, from the
 * bucket and from the day's quota: all or nothing.
 */
class BatchGeocodeChallengeTest extends ApiTest {

    ResultActions batch(String key, String json) throws Exception {
        return mvc.perform(post("/geocode/batch").header("X-Api-Key", key).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    @Test
    void eachAddressCostsOneRequest() throws Exception {
        batch(ZOOMKART, "{\"addresses\":[\"MG Road, Bengaluru\",\"Nowhere Lane\",\"marine drive, mumbai\"]}").andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(3))
                .andExpect(jsonPath("$[0].found").value(true)).andExpect(jsonPath("$[0].place.address").value("MG Road, Bengaluru, Karnataka"))
                .andExpect(jsonPath("$[1].found").value(false)).andExpect(jsonPath("$[1].place").doesNotExist())
                .andExpect(jsonPath("$[2].place.address").value("Marine Drive, Mumbai, Maharashtra"));
        mvc.perform(get("/partners/1/usage").header("X-Api-Key", ZOOMKART)).andExpect(jsonPath("$.usedToday").value(4))   // 3 + this one
                .andExpect(jsonPath("$.tokensLeft").value(6));
    }

    @Test
    void aBatchBiggerThanWhatIsLeftIsRefusedWhole() throws Exception {
        answer(CHALO);   // 2 of its 3 left
        batch(CHALO, "{\"addresses\":[\"a b c\",\"d e f\",\"g h i\"]}").andExpect(status().isTooManyRequests())   // needs 3
                .andExpect(header().string("Retry-After", "1"));
        batch(CHALO, "{\"addresses\":[]}").andExpect(status().isBadRequest());
        batch(CHALO, "{\"addresses\":[" + "\"MG Road, Bengaluru\",".repeat(10) + "\"MG Road, Bengaluru\"]}").andExpect(status().isBadRequest());   // 11
        mvc.perform(get("/partners/2/usage").header("X-Api-Key", CHALO)).andExpect(jsonPath("$.usedToday").value(2)).andExpect(jsonPath("$.tokensLeft").value(1));   // nothing taken by the refused ones
    }
}
