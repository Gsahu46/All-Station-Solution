package com.paysetu.payments;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.resttestclient.autoconfigure.AutoConfigureRestTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.client.RestTestClient;

/** Shared setup: the whole app on a random port, real HTTP, real Postgres, empty tables before each test. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureRestTestClient
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    static final String ASHA_PAYS_RAVI = """
            {"payerVpa":"asha@okpaysetu","payeeVpa":"ravi@oksbi","amountPaise":12550,"note":"Dinner split"}
            """;

    @Autowired
    RestTestClient client;

    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void emptyTables() {
        jdbc.sql("TRUNCATE idempotency_keys, payments").update();
    }

    RestTestClient.ResponseSpec pay(String idempotencyKey, String json) {
        return client.post().uri("/payments")
                .header("Idempotency-Key", idempotencyKey)
                .contentType(MediaType.APPLICATION_JSON)
                .body(json)
                .exchange();
    }

    long paymentCount() {
        return jdbc.sql("SELECT count(*) FROM payments").query(Long.class).single();
    }
}
