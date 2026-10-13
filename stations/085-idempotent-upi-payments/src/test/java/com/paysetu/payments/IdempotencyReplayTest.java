package com.paysetu.payments;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;

/** Replay: the same request twice gives one effect and the same answer. */
class IdempotencyReplayTest extends ApiTest {

    @Test
    void sameKeyAndBodyReplaysTheFirstResponseExactly() {
        String first = pay("replay-key-0001", ASHA_PAYS_RAVI)
                .expectStatus().isCreated()
                .expectHeader().valueEquals("Idempotent-Replayed", "false")
                .expectBody(String.class).returnResult().getResponseBody();

        String second = pay("replay-key-0001", ASHA_PAYS_RAVI)
                .expectStatus().isCreated()
                .expectHeader().valueEquals("Idempotent-Replayed", "true")
                .expectBody(String.class).returnResult().getResponseBody();

        assertThat(second).isEqualTo(first);
        assertThat(paymentCount()).isEqualTo(1);
    }

    @Test
    void sameKeyWithADifferentAmountIs422AndChargesNothingMore() {
        pay("replay-key-0002", ASHA_PAYS_RAVI).expectStatus().isCreated();

        pay("replay-key-0002", ASHA_PAYS_RAVI.replace("12550", "99900"))
                .expectStatus().isEqualTo(422)
                .expectHeader().contentType(MediaType.APPLICATION_PROBLEM_JSON)
                .expectBody().jsonPath("$.title").isEqualTo("Idempotency key reused");

        assertThat(paymentCount()).isEqualTo(1);
    }

    @Test
    void sameKeyWithADifferentPayeeIs422() {
        pay("replay-key-0005", ASHA_PAYS_RAVI).expectStatus().isCreated();
        pay("replay-key-0005", ASHA_PAYS_RAVI.replace("ravi@oksbi", "kiran@okaxis"))
                .expectStatus().isEqualTo(422);
        assertThat(paymentCount()).isEqualTo(1);
    }

    @Test
    void omittedNoteThenEmptyNoteIsAReplay() {
        String noNote = ASHA_PAYS_RAVI.replace(",\"note\":\"Dinner split\"", "");
        pay("replay-key-0006", noNote).expectStatus().isCreated();
        pay("replay-key-0006", ASHA_PAYS_RAVI.replace("Dinner split", ""))
                .expectStatus().isCreated()
                .expectHeader().valueEquals("Idempotent-Replayed", "true");
        assertThat(paymentCount()).isEqualTo(1);
    }

    @Test
    void mixedCaseVpaIsTheSamePayerAndTheSamePayment() {
        pay("replay-key-0007", ASHA_PAYS_RAVI).expectStatus().isCreated();
        pay("replay-key-0007", ASHA_PAYS_RAVI.replace("asha@okpaysetu", "Asha@OKPaysetu"))
                .expectStatus().isCreated()
                .expectHeader().valueEquals("Idempotent-Replayed", "true");
        assertThat(paymentCount()).isEqualTo(1);
    }

    @Test
    void sameContentWithDifferentJsonFormattingIsStillAReplay() {
        pay("replay-key-0003", ASHA_PAYS_RAVI).expectStatus().isCreated();

        String reordered = """
                { "note": "Dinner split",  "amountPaise": 12550,
                  "payeeVpa": "ravi@oksbi", "payerVpa": "asha@okpaysetu" }
                """;
        pay("replay-key-0003", reordered)
                .expectStatus().isCreated()
                .expectHeader().valueEquals("Idempotent-Replayed", "true");
        assertThat(paymentCount()).isEqualTo(1);
    }

    @Test
    void keysAreScopedPerPayerSoTwoCustomersCanPickTheSameKey() {
        pay("my-first-payment", ASHA_PAYS_RAVI).expectStatus().isCreated();
        pay("my-first-payment", ASHA_PAYS_RAVI.replace("asha@okpaysetu", "meera@okhdfc"))
                .expectStatus().isCreated()
                .expectHeader().valueEquals("Idempotent-Replayed", "false");
        assertThat(paymentCount()).isEqualTo(2);
    }

    @Test
    void aFailedValidationDoesNotUseUpTheKey() {
        pay("replay-key-0004", ASHA_PAYS_RAVI.replace("12550", "0")).expectStatus().isBadRequest();
        pay("replay-key-0004", ASHA_PAYS_RAVI)
                .expectStatus().isCreated()
                .expectHeader().valueEquals("Idempotent-Replayed", "false");
    }
}
