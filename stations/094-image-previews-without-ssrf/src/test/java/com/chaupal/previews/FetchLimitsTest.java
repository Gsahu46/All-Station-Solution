package com.chaupal.previews;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** A preview never waits long or reads much: an attacker's slow or endless page cannot tie up the server. */
class FetchLimitsTest extends ApiTest {

    @Test
    void aSlowPageTimesOut() throws Exception {
        long t = System.nanoTime();
        preview(TestSites.url("news.example", "/slow")).andExpect(status().isGatewayTimeout()).andExpect(jsonPath("$.detail").value("The page took too long to answer"));
        assertThat((System.nanoTime() - t) / 1_000_000).isBetween(2_900L, 5_000L);
    }

    @Test
    void aHugePageIsReadOnlyAsFarAsAPreviewNeeds() throws Exception {
        long t = System.nanoTime();
        preview(TestSites.url("news.example", "/huge")).andExpect(status().isCreated()).andExpect(jsonPath("$.title").doesNotExist());
        assertThat((System.nanoTime() - t) / 1_000_000).isLessThan(2_000L);   // the first 512 KB, then the connection is dropped
    }
}
