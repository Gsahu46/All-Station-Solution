package com.streamo.devices;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class DeviceSecurityTest extends ApiTest {

    @Test
    void noTokenIs401() throws Exception {
        mvc.perform(get("/me/devices")).andExpect(status().isUnauthorized()).andExpect(header().string("WWW-Authenticate", "Bearer"));
    }

    @Test
    void aTvMayPlayButNotManageDevices() throws Exception {
        JsonNode tv = login("anika", "Living room TV", "tv");
        devices(access(tv)).andExpect(status().isForbidden()).andExpect(jsonPath("$.title").value("Not allowed"));
        removeDevice(access(tv), tv.get("deviceId").asString()).andExpect(status().isForbidden());
    }

    @Test
    void anotherMembersDeviceIs404AndStaysSignedIn() throws Exception {
        JsonNode anika = login("anika", "Anika's phone", "phone");
        JsonNode rohan = login("rohan", "Rohan's phone", "phone");
        removeDevice(access(rohan), anika.get("deviceId").asString()).andExpect(status().isNotFound());
        devices(access(rohan)).andExpect(jsonPath("$[*].name", contains("Rohan's phone")));   // anika's devices never listed
        refreshRequest(refresh(anika)).andExpect(status().isOk());
    }

    @Test
    void accessTokensEndAfter10MinutesAndRefreshTokensAfter30Days() throws Exception {
        JsonNode phone = login("anika", "Anika's phone", "phone");
        later(Duration.ofMinutes(10).plusSeconds(20));
        devices(access(phone)).andExpect(status().isOk());              // inside the 30-second allowance
        later(Duration.ofSeconds(11));
        devices(access(phone)).andExpect(status().isUnauthorized());
        later(Duration.ofDays(30));
        refreshRequest(refresh(phone)).andExpect(status().isUnauthorized());
    }

    @Test
    void tenParallelRefreshesWithOneTokenGiveOnePairAndEndTheDevice() throws Exception {
        JsonNode phone = login("anika", "Anika's phone", "phone");
        CountDownLatch start = new CountDownLatch(1);
        List<Future<Integer>> results = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 10; i++) {
                results.add(threads.submit(() -> {
                    start.await();
                    return refreshRequest(refresh(phone)).andReturn().getResponse().getStatus();
                }));
            }
            start.countDown();
        }
        List<Integer> statuses = new ArrayList<>();
        for (Future<Integer> f : results) {
            statuses.add(f.get());
        }
        assertThat(statuses).containsOnly(200, 401).filteredOn(s -> s == 200).hasSize(1);
        // The other nine looked like a second holder: the device is ended, the safe side of a race.
        assertThat(revokedReason(phone.get("deviceId").asString())).isEqualTo("reuse");
        assertThat(jdbc.sql("SELECT count(*) FROM refresh_tokens").query(Long.class).single()).isEqualTo(2);
    }

    @Test
    void oddRefreshTokensAre400Or401NeverAnError() throws Exception {
        refreshRequest("not-a-token").andExpect(status().isBadRequest());
        refreshRequest("' OR '1'='1").andExpect(status().isBadRequest());
        refreshRequest("a".repeat(5000)).andExpect(status().isBadRequest());
        refreshRequest("A".repeat(43)).andExpect(status().isUnauthorized());   // the right shape, but not ours
        for (String header : new String[]{"Bearer not.a.jwt", "Bearer " + "a".repeat(5000), "Basic YW5pa2E6YW5pa2EtZGVtby1wYXNz"}) {
            mvc.perform(get("/me/devices").header("Authorization", header)).andExpect(status().isUnauthorized());
        }
    }
}
