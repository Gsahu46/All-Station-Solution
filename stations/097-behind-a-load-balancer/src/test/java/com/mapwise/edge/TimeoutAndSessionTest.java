package com.mapwise.edge;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

import static org.assertj.core.api.Assertions.assertThat;

class TimeoutAndSessionTest extends ApiTest {

    @Autowired
    Uploads uploads;

    /** A client announces 1,000 bytes, sends 10 and stops. Tomcat's read timeout (1 s here) ends it; no thread waits forever. */
    @Test
    void aStalledUploadIsCutOffAndNothingIsStored() throws Exception {
        int before = uploads.all().size();
        try (Socket socket = new Socket()) {
            socket.connect(new InetSocketAddress("127.0.0.1", port));
            socket.setSoTimeout(10_000);
            OutputStream out = socket.getOutputStream();
            out.write(("POST /uploads HTTP/1.1\r\nHost: 127.0.0.1\r\nAuthorization: Basic " + Base64.getEncoder().encodeToString("asha:asha-demo-pass".getBytes())
                    + "\r\nContent-Type: application/octet-stream\r\nContent-Length: 1000\r\n\r\n0123456789").getBytes(StandardCharsets.US_ASCII));
            out.flush();
            long started = System.nanoTime();
            InputStream in = socket.getInputStream();
            String answer = new String(in.readAllBytes(), StandardCharsets.US_ASCII);   // until the server closes
            long seconds = (System.nanoTime() - started) / 1_000_000_000;
            assertThat(seconds).isLessThan(5);
            assertThat(answer).startsWith("HTTP/1.1 408");
        }
        assertThat(uploads.all()).hasSize(before);
    }

    /** Nothing about a user is kept between requests, so any server behind the balancer can answer any request. */
    @Test
    void noSessionCookieSoNoStickySessionsAreNeeded() throws Exception {
        var response = send(BALANCER, as("asha", viaBalancer("/uploads", "198.51.100.7")).POST(java.net.http.HttpRequest.BodyPublishers.ofString("hello")));
        assertThat(response.statusCode()).isEqualTo(201);
        assertThat(response.headers().allValues("Set-Cookie")).isEmpty();
    }
}
