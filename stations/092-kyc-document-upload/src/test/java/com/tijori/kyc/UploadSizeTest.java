package com.tijori.kyc;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Arrays;
import java.util.Base64;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Sizes need the real server: MockMvc never applies the multipart limits, Tomcat does. And the copy stops at the
 * limit without reading the rest, which the last test proves with a 64 MB stream made up as it is read.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = "tijori.storage-dir=target/test-storage/kyc-size")
class UploadSizeTest {

    @LocalServerPort
    int port;

    HttpResponse<String> post(byte[] content) throws Exception {
        String boundary = "----kyc";
        ByteArrayOutputStream body = new ByteArrayOutputStream();
        body.write(("--" + boundary + "\r\nContent-Disposition: form-data; name=\"type\"\r\n\r\nPAN\r\n--" + boundary
                + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\"pan.pdf\"\r\nContent-Type: application/pdf\r\n\r\n").getBytes());
        body.write(content);
        body.write(("\r\n--" + boundary + "--\r\n").getBytes());
        HttpRequest request = HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/kyc/1/documents"))
                .header("Authorization", "Basic " + Base64.getEncoder().encodeToString("asha:asha-demo-pass".getBytes()))
                .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                .POST(HttpRequest.BodyPublishers.ofByteArray(body.toByteArray())).build();
        try (HttpClient client = HttpClient.newHttpClient()) {
            return client.send(request, HttpResponse.BodyHandlers.ofString());
        }
    }

    static byte[] pdfOfSize(int size) {
        return Arrays.copyOf("%PDF-1.7\n".getBytes(), size);
    }

    @Test
    void upToFiveMegabytesIsAcceptedAndMoreIs413() throws Exception {
        long before = storedFiles();
        assertThat(post(pdfOfSize(5 * 1024 * 1024)).statusCode()).isEqualTo(201);
        HttpResponse<String> over = post(pdfOfSize(5 * 1024 * 1024 + 1));
        assertThat(over.statusCode()).isEqualTo(413);
        assertThat(over.body()).contains("Maximum upload size exceeded");   // refused by the server's multipart limit, before our code ran
        // Far over the limit, Tomcat answers 413 and closes the connection without reading the rest (it reads at most
        // 2 MB more by default). curl reads that 413 (see the captures); this Java client, still sending, sees the
        // connection close. Either way nothing is stored. Found while building.
        int huge;
        try {
            huge = post(pdfOfSize(60 * 1024 * 1024)).statusCode();
        } catch (java.io.IOException closed) {
            huge = -1;
        }
        assertThat(huge).isIn(413, -1);
        assertThat(storedFiles()).isEqualTo(before + 1);   // only the 5 MB document
    }

    static long storedFiles() throws java.io.IOException {
        java.nio.file.Path dir = java.nio.file.Path.of("target/test-storage/kyc-size");
        if (!java.nio.file.Files.exists(dir)) {
            return 0;
        }
        try (var files = java.nio.file.Files.walk(dir)) {
            return files.filter(java.nio.file.Files::isRegularFile).count();
        }
    }

    @Test
    void theCopyStopsAtTheLimitWithoutReadingTheRest() {
        long[] read = {0};
        long length = 64L * 1024 * 1024;
        InputStream big = new InputStream() {   // 64 MB of zeros, made up as they are read, never held anywhere
            @Override
            public int read() {
                return read[0] < length ? (int) (++read[0] * 0) : -1;
            }

            @Override
            public int read(byte[] b, int off, int len) {
                if (read[0] >= length) {
                    return -1;
                }
                int n = (int) Math.min(len, length - read[0]);
                read[0] += n;
                return n;
            }
        };
        assertThatThrownBy(() -> DocumentStore.copyAtMost(big, java.io.OutputStream.nullOutputStream(), DocumentStore.MAX_BYTES))
                .isInstanceOf(DocumentStore.TooLarge.class);
        assertThat(read[0]).isLessThanOrEqualTo(DocumentStore.MAX_BYTES + 8192);
    }
}
