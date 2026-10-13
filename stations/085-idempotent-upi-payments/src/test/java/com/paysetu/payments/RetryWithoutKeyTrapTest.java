package com.paysetu.payments;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * The phone sends a payment, the network times out before the reply arrives, the app retries.
 */
@Import(RetryWithoutKeyTrapTest.NaivePaymentController.class)
class RetryWithoutKeyTrapTest extends ApiTest {

    /** The "before" code: every POST charges. Kept only in tests, to show the trap. */
    @RestController
    static class NaivePaymentController {
        private final PaymentRepository payments;

        NaivePaymentController(PaymentRepository payments) {
            this.payments = payments;
        }

        @PostMapping("/naive/payments")
        Payment pay(@RequestBody PaymentRequest req) {
            return payments.insert(req);
        }
    }

    @Test
    void retryWithoutAKeyChargesTheCustomerTwice() {
        for (int attempt = 1; attempt <= 2; attempt++) { // attempt 1 "timed out" on the phone, attempt 2 is the retry
            client.post().uri("/naive/payments").contentType(MediaType.APPLICATION_JSON).body(ASHA_PAYS_RAVI)
                    .exchange().expectStatus().isOk();
        }
        assertThat(paymentCount()).as("the bug: Asha paid Rs 125.50 twice").isEqualTo(2);
    }

    @Test
    void retryWithTheSameKeyChargesOnce() {
        pay("phone-retry-0001", ASHA_PAYS_RAVI).expectStatus().isCreated();
        pay("phone-retry-0001", ASHA_PAYS_RAVI).expectStatus().isCreated();
        assertThat(paymentCount()).as("the fix").isEqualTo(1);
    }
}
