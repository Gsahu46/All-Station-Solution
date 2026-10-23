package com.mapwise.edge;

import org.junit.jupiter.api.Test;

import java.net.http.HttpRequest;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 2: at most 3 uploads a minute from one client address (demo rule). It only works because the address is
 * the real one: with the old way, a client would write a new X-Forwarded-For each time and never be limited.
 */
class UploadsPerClientChallengeTest extends ApiTest {

    int upload(String from, HttpRequest.Builder request) throws Exception {
        return send(from, as("vikram", request).POST(HttpRequest.BodyPublishers.ofString("a file"))).statusCode();
    }

    @Test
    void theFourthUploadInAMinuteFromOneAddressIs429() throws Exception {
        for (int i = 0; i < 3; i++) {
            assertThat(upload(BALANCER, viaBalancer("/uploads", "198.51.100.20"))).isEqualTo(201);
        }
        var fourth = send(BALANCER, as("vikram", viaBalancer("/uploads", "198.51.100.20")).POST(HttpRequest.BodyPublishers.ofString("a file")));
        assertThat(fourth.statusCode()).isEqualTo(429);
        assertThat(fourth.headers().firstValue("Retry-After")).isPresent();
        assertThat(upload(BALANCER, viaBalancer("/uploads", "198.51.100.21"))).isEqualTo(201);   // another client is not affected
    }

    @Test
    void aClientCannotEscapeItsLimitWithMadeUpAddresses() throws Exception {
        for (int i = 0; i < 3; i++) {
            assertThat(upload(DIRECT, request("/uploads").header("X-Forwarded-For", "203.0.113." + i))).isEqualTo(201);
        }
        assertThat(upload(DIRECT, request("/uploads").header("X-Forwarded-For", "203.0.113.99"))).isEqualTo(429);
    }
}
