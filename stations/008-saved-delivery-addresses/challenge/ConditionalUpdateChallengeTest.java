package com.tiffino.addresses;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: Priya edits "home" on her phone while her husband edits it on his. Without a check, the second
 * save silently wipes out the first. With ETag and If-Match, the stale save is refused with 412.
 */
class ConditionalUpdateChallengeTest extends ApiTest {

    private String etag() throws Exception {
        return mvc.perform(get("/customers/42/addresses/home")).andExpect(header().exists("ETag"))
                .andReturn().getResponse().getHeader("ETag");
    }

    @Test
    void aSaveBasedOnAnOldVersionIs412AndChangesNothing() throws Exception {
        putAddress(42, "home", HOME);
        String seenByPriya = etag();
        patchAddress(42, "home", "{\"landmark\":\"Gate 2\"}");                     // her husband's phone saves first
        mvc.perform(put("/customers/42/addresses/home").header("If-Match", seenByPriya)
                        .contentType(MediaType.APPLICATION_JSON).content(HOME.replace("Flat 402", "Flat 403")))
                .andExpect(status().isPreconditionFailed())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
        mvc.perform(get("/customers/42/addresses/home")).andExpect(jsonPath("$.landmark").value("Gate 2"))
                .andExpect(jsonPath("$.line1").value("Flat 402, Lotus Residency"));
    }

    @Test
    void aSaveBasedOnTheCurrentVersionWorksAndReturnsTheNewETag() throws Exception {
        putAddress(42, "home", HOME);
        String current = etag();
        String next = mvc.perform(patch("/customers/42/addresses/home").header("If-Match", current)
                        .contentType("application/merge-patch+json").content("{\"landmark\":\"Gate 2\"}"))
                .andExpect(status().isOk())
                .andExpect(header().exists("ETag"))
                .andReturn().getResponse().getHeader("ETag");
        org.assertj.core.api.Assertions.assertThat(next).isNotEqualTo(current).isEqualTo(etag());
    }

    @Test
    void theSameAddressAlwaysHasTheSameETag() throws Exception {
        putAddress(42, "home", HOME);
        String first = etag();
        putAddress(42, "home", HOME);
        org.assertj.core.api.Assertions.assertThat(etag()).isEqualTo(first);
    }

    @Test
    void withoutIfMatchSavesStillWork() throws Exception {
        putAddress(42, "home", HOME).andExpect(status().isCreated());
        putAddress(42, "home", HOME).andExpect(status().isOk());
    }
}
