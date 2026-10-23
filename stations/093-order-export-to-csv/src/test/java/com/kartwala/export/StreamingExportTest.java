package com.kartwala.export;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Streaming, seen from outside: a million orders (about 80 MB of CSV) on a real port. The first lines arrive long before
 * all rows could have been read: reading them all takes far longer than the export takes to start. Code that loaded
 * every row first could not send a byte sooner than that.
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Import(PostgresTestConfig.class)
class StreamingExportTest {

    @LocalServerPort
    int port;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void aBusyYear() {
        jdbc.sql("TRUNCATE orders, export_log RESTART IDENTITY").update();
        jdbc.sql("""
                INSERT INTO orders (seller_id, order_ref, placed_at, product_name, quantity, amount_paise, buyer_city, status)
                SELECT 1, 'KW-' || n, timestamptz '2026-01-01 00:00+05:30' + n * interval '30 seconds', 'Cotton kurta, blue', 1, 129900, 'Pune', 'PLACED'
                FROM generate_series(1, 1000000) AS n""").update();
        // Fresh statistics, as autovacuum would gather: without them the planner guessed 15 rows and chose to sort.
        jdbc.sql("ANALYZE orders").update();
    }

    @AfterEach
    void demoOrdersBack() throws Exception {
        jdbc.sql("TRUNCATE orders, export_log RESTART IDENTITY").update();
        jdbc.sql(java.nio.file.Files.readString(java.nio.file.Path.of("src/main/resources/db/migration/V2__demo_orders.sql"))).update();
    }

    HttpRequest export(String from, String to) {
        return HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/seller/orders/export?from=" + from + "&to=" + to))
                .header("Authorization", "Basic " + Base64.getEncoder().encodeToString("neha.store:neha-demo-pass".getBytes())).build();
    }

    @Test
    void theFirstLinesArriveLongBeforeAllRowsCouldHaveBeenRead() throws Exception {
        long[] rows = {0};
        long t = System.nanoTime();
        // Outside a transaction the driver reads every row before handing over the first: what loading it all costs.
        jdbc.sql("SELECT order_ref, placed_at, product_name, quantity, amount_paise, buyer_city, status FROM orders WHERE seller_id = 1")
                .query(rs -> {
                    rows[0]++;
                });
        long readAllMs = (System.nanoTime() - t) / 1_000_000;
        assertThat(rows[0]).isEqualTo(1_000_000);
        try (HttpClient client = HttpClient.newHttpClient()) {
            long requestMs = Long.MAX_VALUE;
            for (int i = 0; i < 3; i++) {   // no orders: the cost of a request and its sign-in (bcrypt), the fastest of three
                t = System.nanoTime();
                client.send(export("2027-01-01", "2027-01-01"), HttpResponse.BodyHandlers.ofString());
                requestMs = Math.min(requestMs, (System.nanoTime() - t) / 1_000_000);
            }
            t = System.nanoTime();
            HttpResponse<InputStream> response = client.send(export("2026-01-01", "2026-12-31"), HttpResponse.BodyHandlers.ofInputStream());
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(response.body(), StandardCharsets.UTF_8))) {
                assertThat(reader.readLine()).endsWith(OrderExport.HEADER);
                assertThat(reader.readLine()).startsWith("KW-1,");
                long firstLinesMs = (System.nanoTime() - t) / 1_000_000;
                System.out.printf("STREAMING first lines after %d ms, a request alone %d ms, reading every row %d ms%n", firstLinesMs, requestMs, readAllMs);
                assertThat(firstLinesMs - requestMs).as("first lines after %d ms, a request alone %d ms, reading every row %d ms", firstLinesMs, requestMs, readAllMs)
                        .isLessThan(readAllMs / 2);
                assertThat(reader.lines().count()).isEqualTo(999_999);
            }
        }
    }
}
