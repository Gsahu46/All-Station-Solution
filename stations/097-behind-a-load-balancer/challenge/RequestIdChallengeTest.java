package com.mapwise.edge;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Challenge 1: every answer carries X-Request-Id, so one request can be followed through the balancer's log and the
 * app's. The balancer's id is kept; a client's own is not trusted (it could reuse someone else's to muddle the logs).
 */
class RequestIdChallengeTest extends ApiTest {

    static final String UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

    @Test
    void theBalancersIdIsKept() throws Exception {
        var response = send(BALANCER, viaBalancer("/whoami", "198.51.100.7").header("X-Request-Id", "lb-7f3a9c"));
        assertThat(response.headers().firstValue("X-Request-Id")).hasValue("lb-7f3a9c");
    }

    @Test
    void aClientsOwnIdIsReplacedAndAMissingOneIsMade() throws Exception {
        var direct = send(DIRECT, request("/whoami").header("X-Request-Id", "lb-7f3a9c"));
        assertThat(direct.headers().firstValue("X-Request-Id").orElseThrow()).matches(UUID);
        var none = send(BALANCER, viaBalancer("/whoami", "198.51.100.7"));
        assertThat(none.headers().firstValue("X-Request-Id").orElseThrow()).matches(UUID);
        var unauthorised = send(BALANCER, viaBalancer("/uploads", "198.51.100.7").POST(java.net.http.HttpRequest.BodyPublishers.ofString("x")));
        assertThat(unauthorised.statusCode()).isEqualTo(401);
        assertThat(unauthorised.headers().firstValue("X-Request-Id")).isPresent();   // errors too: they are what you look up
    }
}
