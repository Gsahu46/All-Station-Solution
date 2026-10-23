package com.chaupal.previews;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: chaupal.previews.allowed-domains, when set, limits previews to those sites and their subdomains. A name
 * that merely ends with the same letters is another site. The address rules still apply to allowed sites.
 */
@TestPropertySource(properties = "chaupal.previews.allowed-domains=news.example,rebind.example")
class AllowedDomainsChallengeTest extends ApiTest {

    @Test
    void onlyListedSitesCanBePreviewed() throws Exception {
        preview(TestSites.url("news.example", "/article")).andExpect(status().isCreated());
        preview(TestSites.url("mixed.example", "/article")).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("This site cannot be previewed"));
        preview(TestSites.url("fakenews.example", "/article")).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("This site cannot be previewed"));
        preview(TestSites.url("127.0.0.2", "/article")).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("This site cannot be previewed"));
    }
}
