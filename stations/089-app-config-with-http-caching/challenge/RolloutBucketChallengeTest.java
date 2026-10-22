package com.streamo.config;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: a gradual rollout. The app sends bucket=0..99 (from a hash of its install id, stable per install).
 * Demo rule: watchParty is on for buckets 0 to 9 (10%). Answers depend on whether the bucket is in, not on the bucket
 * itself, so all installs on the same side share one ETag and caches stay useful.
 */
class RolloutBucketChallengeTest extends ApiTest {

    @Test
    void tenPercentGetTheFeature() throws Exception {
        mvc.perform(config("android", "6.1.0").param("bucket", "5")).andExpect(status().isOk()).andExpect(jsonPath("$.features.watchParty").value(true));
        mvc.perform(config("android", "6.1.0").param("bucket", "10")).andExpect(jsonPath("$.features.watchParty").value(false));
        mvc.perform(config("android", "6.1.0")).andExpect(jsonPath("$.features.watchParty").value(false));
        mvc.perform(config("android", "6.1.0").param("bucket", "100")).andExpect(status().isBadRequest());
    }

    @Test
    void bucketsOnTheSameSideShareOneETag() throws Exception {
        String in3 = mvc.perform(config("android", "6.1.0").param("bucket", "3")).andReturn().getResponse().getHeader("ETag");
        String in7 = mvc.perform(config("android", "6.1.0").param("bucket", "7")).andReturn().getResponse().getHeader("ETag");
        String out50 = mvc.perform(config("android", "6.1.0").param("bucket", "50")).andReturn().getResponse().getHeader("ETag");
        String none = mvc.perform(config("android", "6.1.0")).andReturn().getResponse().getHeader("ETag");
        assertThat(in3).isEqualTo(in7);
        assertThat(out50).isEqualTo(none).isNotEqualTo(in3);
    }
}
