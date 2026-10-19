package com.streamo.devices;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class DeviceContractTest extends ApiTest {

    @Test
    void loginGivesAShortAccessTokenAndARefreshTokenForThisDevice() throws Exception {
        loginRequest("Anika@Example.com", "anika-demo-pass", "Anika's phone", "phone").andExpect(status().isOk())
                .andExpect(jsonPath("$.tokenType").value("Bearer")).andExpect(jsonPath("$.expiresIn").value(600))
                .andExpect(jsonPath("$.accessToken").value(matchesPattern("[\\w-]+\\.[\\w-]+\\.[\\w-]+")))
                .andExpect(jsonPath("$.refreshToken").value(matchesPattern("[\\w-]{43}")))
                .andExpect(jsonPath("$.deviceId").value(matchesPattern("[0-9a-f-]{36}")));
    }

    @Test
    void refreshGivesANewPairAndTheOldRefreshTokenIsUsedUp() throws Exception {
        JsonNode first = login("anika", "Anika's phone", "phone");
        JsonNode second = body(refreshRequest(refresh(first)).andExpect(status().isOk()).andExpect(jsonPath("$.deviceId").value(first.get("deviceId").asString())));
        assertThat(refresh(second)).isNotEqualTo(refresh(first));
        assertThat(jdbc.sql("SELECT count(*) FROM refresh_tokens WHERE used_at IS NULL").query(Long.class).single()).isEqualTo(1);
        refreshRequest(refresh(second)).andExpect(status().isOk());   // the chain goes on
    }

    @Test
    void theDeviceListShowsOnlyActiveDevicesAndMarksThisOne() throws Exception {
        JsonNode phone = login("anika", "Anika's phone", "phone");
        later(java.time.Duration.ofMinutes(1));   // listed oldest first
        login("anika", "Living room TV", "tv");
        later(java.time.Duration.ofMinutes(1));
        JsonNode laptop = login("anika", "Anika's laptop", "web");
        logout(access(laptop)).andExpect(status().isNoContent());
        devices(access(phone)).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].name", contains("Anika's phone", "Living room TV")))
                .andExpect(jsonPath("$[*].current", contains(true, false)));
    }

    @Test
    void logoutEndsThisDeviceOnly() throws Exception {
        JsonNode phone = login("anika", "Anika's phone", "phone");
        JsonNode laptop = login("anika", "Anika's laptop", "web");
        logout(access(phone)).andExpect(status().isNoContent());
        refreshRequest(refresh(phone)).andExpect(status().isUnauthorized()).andExpect(jsonPath("$.detail").value("Sign in again on this device"));
        assertThat(revokedReason(phone.get("deviceId").asString())).isEqualTo("logout");
        refreshRequest(refresh(laptop)).andExpect(status().isOk());
    }

    @Test
    void wrongLoginsAre401AndBadBodiesAre400() throws Exception {
        loginRequest("anika@example.com", "not-her-password", "x", "phone").andExpect(status().isUnauthorized()).andExpect(jsonPath("$.detail").value("Wrong email or password"));
        loginRequest("nobody@example.com", "any-password", "x", "phone").andExpect(status().isUnauthorized()).andExpect(jsonPath("$.detail").value("Wrong email or password"));
        loginRequest("anika@example.com", "anika-demo-pass", "x", "fridge").andExpect(status().isBadRequest());
        loginRequest("anika@example.com", "anika-demo-pass", " ", "phone").andExpect(status().isBadRequest());
        loginRequest("anika@example.com", "anika-demo-pass", "x".repeat(61), "phone").andExpect(status().isBadRequest());
    }

    @Test
    void anUnknownDeviceIs404AndABadIdIs400() throws Exception {
        String token = access(login("anika", "Anika's phone", "phone"));
        removeDevice(token, "00000000-0000-0000-0000-000000000000").andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such device"));
        removeDevice(token, "not-a-uuid").andExpect(status().isBadRequest());
    }
}
