package com.streamo.devices;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import java.time.Duration;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Written first. The old design: one refresh token per sign-in, stored as it is, valid for a year, never replaced,
 * and a "log out of all devices" button that only cleared the app's screen. Then the same theft against the real API.
 */
class NeverRotatingTokenTrapTest extends ApiTest {

    /** The old token store, as it was: token text to member, nothing else. */
    static final class OldTokenStore {
        final Map<String, String> tokens = new HashMap<>();

        String signIn(String member) {
            String token = UUID.randomUUID().toString();
            tokens.put(token, member);
            return token;
        }

        String refresh(String token) {
            return tokens.get(token);   // the same token, every time, for a year
        }

        void logOutOfAllDevices(String member) {
            // the old button: a new access token on this screen, nothing removed from the store
        }
    }

    @Test
    void theOldTokenKeptWorkingForMonthsAfterItWasStolen() {
        OldTokenStore old = new OldTokenStore();
        String anikasToken = old.signIn("anika");
        String stolenCopy = anikasToken;              // copied off a shared laptop
        old.refresh(anikasToken);                     // anika keeps watching; her token never changes
        old.logOutOfAllDevices("anika");              // she notices and presses the button
        assertThat(old.refresh(stolenCopy)).isEqualTo("anika");   // months later, still anika
        assertThat(old.tokens).containsKey(anikasToken);          // and the table holds the token itself
    }

    @Test
    void aStolenRefreshTokenUsedAfterTheOwnerEndsTheWholeDevice() throws Exception {
        JsonNode phone = login("anika", "Anika's phone", "phone");
        String stolenCopy = refresh(phone);
        JsonNode next = body(refreshRequest(refresh(phone)).andExpect(status().isOk()));   // anika's app rotates
        assertThat(refresh(next)).isNotEqualTo(stolenCopy);

        refreshRequest(stolenCopy).andExpect(status().isUnauthorized());   // the thief: a used token, a second holder
        assertThat(revokedReason(phone.get("deviceId").asString())).isEqualTo("reuse");
        refreshRequest(refresh(next)).andExpect(status().isUnauthorized());   // anika signs in again; the thief is out for good
        devices(access(next)).andExpect(status().isUnauthorized());
    }

    @Test
    void theThiefRefreshingFirstIsCaughtWhenTheOwnerRefreshes() throws Exception {
        JsonNode phone = login("anika", "Anika's phone", "phone");
        JsonNode thief = body(refreshRequest(refresh(phone)).andExpect(status().isOk()));   // the thief is quicker
        refreshRequest(refresh(phone)).andExpect(status().isUnauthorized());               // anika's app: already used
        refreshRequest(refresh(thief)).andExpect(status().isUnauthorized());               // so the thief's new one dies too
    }

    @Test
    void removingADeviceStopsItsAccessTokenAtOnce() throws Exception {
        JsonNode phone = login("anika", "Anika's phone", "phone");
        JsonNode laptop = login("anika", "Anika's laptop", "web");
        devices(access(phone)).andExpect(status().isOk());
        removeDevice(access(laptop), phone.get("deviceId").asString()).andExpect(status().isNoContent());
        later(Duration.ofSeconds(1));
        devices(access(phone)).andExpect(status().isUnauthorized());     // not in 10 minutes: now
        refreshRequest(refresh(phone)).andExpect(status().isUnauthorized());
        devices(access(laptop)).andExpect(status().isOk());
    }

    @Test
    void theDatabaseHoldsOnlyAHashOfEachRefreshToken() throws Exception {
        String token = refresh(login("anika", "Anika's phone", "phone"));
        assertThat(jdbc.sql("SELECT token_hash FROM refresh_tokens").query(String.class).single())
                .isEqualTo(Sessions.sha256(token)).isNotEqualTo(token);
    }
}
