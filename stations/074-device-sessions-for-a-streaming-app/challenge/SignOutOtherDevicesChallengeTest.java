package com.streamo.devices;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: the button that did nothing. DELETE /me/devices signs out every other device of this member at once
 * (204), keeps this one, and leaves other members alone. A TV may not press it (403).
 */
class SignOutOtherDevicesChallengeTest extends ApiTest {

    @Test
    void everyOtherDeviceIsSignedOutAtOnce() throws Exception {
        JsonNode phone = login("anika", "Anika's phone", "phone");
        JsonNode tv = login("anika", "Living room TV", "tv");
        JsonNode laptop = login("anika", "Anika's laptop", "web");
        JsonNode rohan = login("rohan", "Rohan's phone", "phone");
        mvc.perform(delete("/me/devices").header("Authorization", "Bearer " + access(phone))).andExpect(status().isNoContent());
        devices(access(phone)).andExpect(jsonPath("$[*].name", contains("Anika's phone")));
        devices(access(laptop)).andExpect(status().isUnauthorized());
        refreshRequest(refresh(tv)).andExpect(status().isUnauthorized());
        refreshRequest(refresh(rohan)).andExpect(status().isOk());
    }

    @Test
    void aTvCannotSignOutTheOthers() throws Exception {
        JsonNode tv = login("anika", "Living room TV", "tv");
        mvc.perform(delete("/me/devices").header("Authorization", "Bearer " + access(tv))).andExpect(status().isForbidden());
    }
}
