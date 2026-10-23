package com.mapwise.edge;

import org.junit.jupiter.api.Test;

import java.net.http.HttpRequest;
import java.security.MessageDigest;
import java.util.HexFormat;

import static org.assertj.core.api.Assertions.assertThat;

class ProxyContractTest extends ApiTest {

    @Test
    void aDirectRequestIsTakenAsItIs() throws Exception {
        var me = json(send(DIRECT, request("/whoami")));
        assertThat(me.get("clientIp").asString()).isEqualTo(DIRECT);
        assertThat(me.get("scheme").asString()).isEqualTo("http");
        assertThat(me.get("secure").asBoolean()).isFalse();
        assertThat(me.get("url").asString()).isEqualTo("http://127.0.0.1:" + port + "/whoami");
    }

    @Test
    void throughTheBalancerTheAppSeesTheClientHttpsAndThePublicName() throws Exception {
        var response = send(BALANCER, viaBalancer("/whoami", "198.51.100.7"));
        assertThat(response.statusCode()).isEqualTo(200);
        var me = json(response);
        assertThat(me.get("clientIp").asString()).isEqualTo("198.51.100.7");
        assertThat(me.get("scheme").asString()).isEqualTo("https");
        assertThat(me.get("secure").asBoolean()).isTrue();
        assertThat(me.get("host").asString()).isEqualTo("maps.mapwise.example");
        assertThat(me.get("port").asInt()).isEqualTo(443);
        assertThat(me.get("url").asString()).isEqualTo("https://maps.mapwise.example/whoami");
    }

    @Test
    void anUploadIsCountedAndItsLocationIsThePublicHttpsAddress() throws Exception {
        byte[] file = new byte[1024 * 1024];   // exactly the limit in these tests
        new java.util.Random(97).nextBytes(file);
        var created = send(BALANCER, as("asha", viaBalancer("/uploads", "198.51.100.8")).POST(HttpRequest.BodyPublishers.ofByteArray(file)));
        assertThat(created.statusCode()).isEqualTo(201);
        String location = created.headers().firstValue("Location").orElseThrow();
        assertThat(location).matches("https://maps\\.mapwise\\.example/uploads/\\d+");   // not http://127.0.0.1:port/...
        var body = json(created);
        assertThat(body.get("owner").asString()).isEqualTo("asha");
        assertThat(body.get("bytes").asLong()).isEqualTo(file.length);
        assertThat(body.get("sha256").asString()).isEqualTo(HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(file)));
        assertThat(body.get("clientIp").asString()).isEqualTo("198.51.100.8");

        String path = location.substring("https://maps.mapwise.example".length());
        assertThat(send(BALANCER, as("asha", viaBalancer(path, "198.51.100.8"))).statusCode()).isEqualTo(200);
        assertThat(send(BALANCER, as("asha", viaBalancer("/uploads/999", "198.51.100.8"))).statusCode()).isEqualTo(404);
        // One byte over: 413 before a byte is read. (Far over, Tomcat answers and closes the connection rather than read the rest.)
        var tooBig = send(BALANCER, as("asha", viaBalancer("/uploads", "198.51.100.8")).POST(HttpRequest.BodyPublishers.ofByteArray(new byte[file.length + 1])));
        assertThat(tooBig.statusCode()).isEqualTo(413);
    }
}
