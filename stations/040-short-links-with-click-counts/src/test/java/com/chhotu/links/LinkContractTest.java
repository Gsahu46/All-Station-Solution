package com.chhotu.links;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: create, follow, count, and every refusal. */
class LinkContractTest extends ApiTest {

    static final String LONG_URL = "https://shop.example/diwali-sale?utm_source=sms&utm_medium=bulk&utm_campaign=diwali2026&utm_content=variant-b";

    String code(String body) {
        return body.replaceAll(".*\"code\":\"([^\"]+)\".*", "$1");
    }

    @Test
    void aLinkGetsASevenCharacterCodeAndAShortUrl() throws Exception {
        String body = create(LONG_URL).andExpect(status().isCreated())
                .andExpect(jsonPath("$.code").value(matchesPattern("[0-9A-Za-z]{7}")))
                .andExpect(jsonPath("$.targetUrl").value(LONG_URL))
                .andExpect(header().string("Location", matchesPattern("http://localhost:8080/[0-9A-Za-z]{7}")))
                .andReturn().getResponse().getContentAsString();
        create(LONG_URL).andExpect(jsonPath("$.code").value(org.hamcrest.Matchers.not(code(body))));   // a new link each time
    }

    @Test
    void followingALinkIsATemporaryRedirectAndCounts() throws Exception {
        String code = code(create(LONG_URL).andReturn().getResponse().getContentAsString());
        follow(code).andExpect(status().isFound()).andExpect(header().string("Location", LONG_URL));
        follow(code).andExpect(status().isFound());
        mvc.perform(get("/links/{c}/stats", code)).andExpect(status().isOk())
                .andExpect(jsonPath("$.clicks").value(2)).andExpect(jsonPath("$.targetUrl").value(LONG_URL));
    }

    @Test
    void unknownCodesAre404() throws Exception {
        follow("zzzzzzz").andExpect(status().isNotFound()).andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
        follow("short").andExpect(status().isNotFound());
        mvc.perform(get("/links/zzzzzzz/stats")).andExpect(status().isNotFound());
    }

    @Test
    void onlyWebAddressesCanBeShortened() throws Exception {
        create("javascript:alert(document.cookie)").andExpect(status().isBadRequest());
        create("data:text/html,<script>alert(1)</script>").andExpect(status().isBadRequest());
        create("ftp://files.example.com/a").andExpect(status().isBadRequest());
        create("https://").andExpect(status().isBadRequest());
        create("not a url").andExpect(status().isBadRequest());
        create("HTTPS://Example.com/Path").andExpect(status().isCreated());
    }

    @Test
    void badBodiesAre400() throws Exception {
        create("").andExpect(status().isBadRequest());
        create("https://example.com/" + "a".repeat(2048)).andExpect(status().isBadRequest());
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post("/links").contentType(MediaType.APPLICATION_JSON)
                .content("{\"targetUrl\":\"https://example.com\",\"code\":\"mycode\"}")).andExpect(status().isBadRequest());
    }
}
