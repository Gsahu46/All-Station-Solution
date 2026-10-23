package com.mapwise.edge;

import org.junit.jupiter.api.Test;

import java.net.http.HttpRequest;

import static org.assertj.core.api.Assertions.assertThat;

class ProxySecurityTest extends ApiTest {

    static final String OFFICE = "203.0.113.9";
    static final String HOME = "198.51.100.7";

    @Test
    void withoutASignInUploadsAre401() throws Exception {
        assertThat(send(BALANCER, viaBalancer("/uploads", HOME).POST(HttpRequest.BodyPublishers.ofString("x"))).statusCode()).isEqualTo(401);
        assertThat(send(BALANCER, viaBalancer("/uploads", HOME).header("Authorization", "Basic YXNoYTp3cm9uZw==")
                .POST(HttpRequest.BodyPublishers.ofString("x"))).statusCode()).isEqualTo(401);
        assertThat(send(BALANCER, viaBalancer("/admin/uploads", OFFICE)).statusCode()).isEqualTo(401);
    }

    @Test
    void theAdminListIsForAdminsInTheOfficeOnly() throws Exception {
        assertThat(send(BALANCER, as("ops", viaBalancer("/admin/uploads", OFFICE))).statusCode()).isEqualTo(200);
        assertThat(send(BALANCER, as("ops", viaBalancer("/admin/uploads", HOME))).statusCode()).isEqualTo(403);
        assertThat(send(BALANCER, as("asha", viaBalancer("/admin/uploads", OFFICE))).statusCode()).isEqualTo(403);
    }

    @Test
    void aUserCannotReadAnotherUsersUpload() throws Exception {
        var created = send(BALANCER, as("asha", viaBalancer("/uploads", HOME)).POST(HttpRequest.BodyPublishers.ofString("asha's file")));
        String path = "/uploads/" + json(created).get("id").asLong();
        assertThat(send(BALANCER, as("vikram", viaBalancer(path, HOME))).statusCode()).isEqualTo(404);
        assertThat(send(BALANCER, as("asha", viaBalancer(path, HOME))).statusCode()).isEqualTo(200);
    }

    @Test
    void maliciousForwardedHeadersGiveNothingAway() throws Exception {
        // Not an address, through the balancer: never the office, and no error.
        assertThat(send(BALANCER, as("ops", viaBalancer("/admin/uploads", "not-an-ip"))).statusCode()).isEqualTo(403);
        assertThat(send(BALANCER, as("ops", viaBalancer("/admin/uploads", "203.0.113.9.evil.example"))).statusCode()).isEqualTo(403);
        // A made-up protocol is not https.
        var me = json(send(BALANCER, request("/whoami").header("X-Forwarded-For", HOME).header("X-Forwarded-Proto", "javascript")));
        assertThat(me.get("secure").asBoolean()).isFalse();
        // Two X-Forwarded-For headers, the first written by the client: still the balancer's entry.
        var twice = send(BALANCER, request("/whoami").header("X-Forwarded-For", OFFICE).header("X-Forwarded-For", HOME));
        assertThat(json(twice).get("clientIp").asString()).isEqualTo(HOME);
        // A long chain of made-up hops before the real one.
        var chain = send(BALANCER, request("/whoami").header("X-Forwarded-For", (OFFICE + ", ").repeat(50) + HOME));
        assertThat(json(chain).get("clientIp").asString()).isEqualTo(HOME);
    }
}
