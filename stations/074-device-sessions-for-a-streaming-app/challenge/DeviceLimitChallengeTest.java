package com.streamo.devices;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import java.time.Duration;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: demo rule, at most 5 signed-in devices per member. Signing in on a sixth signs out the one used
 * longest ago, with revoked_reason 'limit' (a new value the database must accept).
 */
class DeviceLimitChallengeTest extends ApiTest {

    @Test
    void aSixthDeviceSignsOutTheLeastRecentlyUsed() throws Exception {
        JsonNode first = login("anika", "Device 1", "web");
        for (int i = 2; i <= 5; i++) {
            later(Duration.ofMinutes(1));
            login("anika", "Device " + i, "web");
        }
        later(Duration.ofMinutes(1));
        JsonNode sixth = login("anika", "Device 6", "phone");
        devices(access(sixth)).andExpect(jsonPath("$", hasSize(5)));
        refreshRequest(refresh(first)).andExpect(status().isUnauthorized());
        assertThat(revokedReason(first.get("deviceId").asString())).isEqualTo("limit");
    }
}
