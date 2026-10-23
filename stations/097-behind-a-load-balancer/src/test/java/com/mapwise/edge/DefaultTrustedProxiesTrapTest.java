package com.mapwise.edge;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;

import java.net.InetAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Base64;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The second half of the trap: forward headers on, but Spring Boot's default list of trusted proxies (every private
 * and loopback range, copied from Boot 4.1.1's own metadata). Any machine inside the network can then claim any address.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = "server.tomcat.remoteip.internal-proxies="
        + "192.168.0.0/16, 172.16.0.0/12, 169.254.0.0/16, fc00::/7, 10.0.0.0/8, 100.64.0.0/10, 127.0.0.0/8, fe80::/10, ::1/128")
class DefaultTrustedProxiesTrapTest {

    @LocalServerPort
    int port;

    @Test
    void withBootsDefaultListAMachineInsideTheNetworkCanBeTheOffice() throws Exception {
        HttpRequest request = HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + port + "/admin/uploads"))
                .header("Authorization", "Basic " + Base64.getEncoder().encodeToString("ops:ops-demo-pass".getBytes()))
                .header("X-Forwarded-For", "203.0.113.9").build();
        try (HttpClient fromAnotherMachine = HttpClient.newBuilder().localAddress(InetAddress.getByName("127.0.0.2")).build()) {
            // 127.0.0.2 is not the balancer, but it is in 127.0.0.0/8: trusted, so its made-up header is believed.
            assertThat(fromAnotherMachine.send(request, HttpResponse.BodyHandlers.ofString()).statusCode()).isEqualTo(200);
        }
    }
}
