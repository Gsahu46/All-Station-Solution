package com.mapwise.edge;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/** A client outside the office writes the office's address into X-Forwarded-For. Written first. */
class SpoofedClientIpTrapTest extends ApiTest {

    /** The old way: the first address in X-Forwarded-For is the client. Whoever sent the header. */
    static String oldClientIp(String forwardedFor, String remoteAddr) {
        return forwardedFor == null ? remoteAddr : forwardedFor.split(",")[0].strip();
    }

    @Test
    void theOldWayBelievesWhateverTheClientWrites() {
        // Straight to the app, and through the balancer (which appends the real address): the old way sees the office both times.
        assertThat(oldClientIp("203.0.113.9", DIRECT)).isEqualTo("203.0.113.9");
        assertThat(oldClientIp("203.0.113.9, 198.51.100.7", BALANCER)).isEqualTo("203.0.113.9");
        assertThat(SecurityConfig.fromNetwork(new org.springframework.security.web.util.matcher.IpAddressMatcher("203.0.113.0/24"), "203.0.113.9")).isTrue();
    }

    @Test
    void theApiTrustsTheHeaderOnlyFromTheBalancerAndOnlyItsLastEntry() throws Exception {
        var direct = send(DIRECT, as("ops", request("/admin/uploads")).header("X-Forwarded-For", "203.0.113.9"));
        assertThat(direct.statusCode()).isEqualTo(403);   // the header from a client is ignored: it is 127.0.0.2
        var spoofedThroughBalancer = send(BALANCER, as("ops", viaBalancer("/admin/uploads", "203.0.113.9, 198.51.100.7")));
        assertThat(spoofedThroughBalancer.statusCode()).isEqualTo(403);   // the balancer's entry, 198.51.100.7, is the client
        assertThat(json(send(BALANCER, viaBalancer("/whoami", "203.0.113.9, 198.51.100.7"))).get("clientIp").asString()).isEqualTo("198.51.100.7");
        assertThat(json(send(DIRECT, request("/whoami").header("X-Forwarded-For", "203.0.113.9"))).get("clientIp").asString()).isEqualTo(DIRECT);
    }
}
