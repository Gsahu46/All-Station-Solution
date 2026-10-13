package com.paysetu.payments;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/** HTTP contract: status codes, headers and bodies a client can rely on. */
class PaymentContractTest extends ApiTest {

    @Test
    void validPaymentReturns201WithLocationAndBody() {
        pay("contract-key-001", ASHA_PAYS_RAVI)
                .expectStatus().isCreated()
                .expectHeader().valueMatches("Location", "/payments/[0-9a-f-]{36}")
                .expectHeader().valueEquals("Idempotent-Replayed", "false")
                .expectBody()
                .jsonPath("$.paymentId").isNotEmpty()
                .jsonPath("$.payerVpa").isEqualTo("asha@okpaysetu")
                .jsonPath("$.payeeVpa").isEqualTo("ravi@oksbi")
                .jsonPath("$.amountPaise").isEqualTo(12550)
                .jsonPath("$.status").isEqualTo("SUCCESS")
                .jsonPath("$.createdAt").isNotEmpty();
    }

    @Test
    void createdPaymentCanBeReadBack() {
        String created = pay("contract-key-002", ASHA_PAYS_RAVI)
                .expectStatus().isCreated()
                .expectBody(String.class).returnResult().getResponseBody();
        String id = created.replaceAll(".*\"paymentId\":\"([^\"]+)\".*", "$1").trim();

        client.get().uri("/payments/{id}", id).exchange()
                .expectStatus().isOk()
                .expectBody().json(created);
    }

    @Test
    void unknownPaymentIs404Problem() {
        client.get().uri("/payments/{id}", UUID.randomUUID()).exchange()
                .expectStatus().isNotFound()
                .expectHeader().contentType(MediaType.APPLICATION_PROBLEM_JSON)
                .expectBody().jsonPath("$.title").isEqualTo("Payment not found");
    }

    @Test
    void invalidFieldsAre400WithOneMessagePerField() {
        pay("contract-key-003", """
                {"payerVpa":"asha","payeeVpa":"ravi@oksbi","amountPaise":0}
                """)
                .expectStatus().isBadRequest()
                .expectHeader().contentType(MediaType.APPLICATION_PROBLEM_JSON)
                .expectBody()
                .jsonPath("$.errors.payerVpa").isEqualTo("must look like name@bank")
                .jsonPath("$.errors.amountPaise").isEqualTo("must be greater than 0");
        assertThat(paymentCount()).isZero();
    }

    @Test
    void amountAboveTheLimitIs400() {
        pay("contract-key-004", ASHA_PAYS_RAVI.replace("12550", "10000001"))
                .expectStatus().isBadRequest()
                .expectBody().jsonPath("$.errors.amountPaise").isEqualTo("must not exceed Rs 1,00,000 per payment");
    }

    @Test
    void payingYourselfIs400() {
        pay("contract-key-005", ASHA_PAYS_RAVI.replace("ravi@oksbi", "ASHA@okpaysetu"))
                .expectStatus().isBadRequest()
                .expectBody().jsonPath("$.errors.differentParties").isEqualTo("payer and payee must be different");
    }

    @Test
    void missingIdempotencyKeyIs400() {
        client.post().uri("/payments").contentType(MediaType.APPLICATION_JSON).body(ASHA_PAYS_RAVI).exchange()
                .expectStatus().isBadRequest()
                .expectBody().jsonPath("$.detail").isEqualTo("Required header 'Idempotency-Key' is not present.");
        assertThat(paymentCount()).isZero();
    }

    @Test
    void malformedIdempotencyKeyIs400() {
        pay("short", ASHA_PAYS_RAVI)
                .expectStatus().isBadRequest()
                .expectBody().jsonPath("$.errors.idempotencyKey").exists();
    }

    @Test
    void brokenJsonIs400() {
        pay("contract-key-006", "{\"payerVpa\":")
                .expectStatus().isBadRequest()
                .expectHeader().contentType(MediaType.APPLICATION_PROBLEM_JSON);
    }
}
