package com.paysetu.payments;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.reset;

/** The database is the last line of defence: constraints hold even if Java validation is bypassed, and failures roll back. */
class PaymentDatabaseTest extends ApiTest {

    @MockitoSpyBean
    IdempotencyKeyRepository keys;

    @Test
    void databaseRejectsAmountsOutsideTheRangeEvenWithoutJavaValidation() {
        for (long paise : new long[] {0, 10_000_001}) {
            assertThatThrownBy(() -> insertPayment("asha@okpaysetu", "ravi@oksbi", paise))
                    .isInstanceOf(DataIntegrityViolationException.class)
                    .hasMessageContaining("payments_amount_range");
        }
        insertPayment("asha@okpaysetu", "ravi@oksbi", 10_000_000); // the maximum itself is allowed
    }

    @Test
    void databaseRejectsPayingYourselfInAnyLetterCase() {
        assertThatThrownBy(() -> insertPayment("asha@okpaysetu", "ASHA@okpaysetu", 100))
                .isInstanceOf(DataIntegrityViolationException.class)
                .hasMessageContaining("payments_different_parties");
    }

    @Test
    void databaseRejectsAHalfFilledStoredResponse() {
        UUID paymentId = insertPayment("asha@okpaysetu", "ravi@oksbi", 100);
        assertThatThrownBy(() -> jdbc.sql("""
                INSERT INTO idempotency_keys (payer_vpa, idem_key, request_hash, payment_id, response_status)
                VALUES ('asha@okpaysetu', 'k-0002', ?, ?, 201)
                """).params("a".repeat(64), paymentId).update()) // body missing
                .isInstanceOf(DataIntegrityViolationException.class)
                .hasMessageContaining("idempotency_keys_result_complete");
    }

    private UUID insertPayment(String payer, String payee, long paise) {
        UUID id = UUID.randomUUID();
        jdbc.sql("""
                INSERT INTO payments (id, payer_vpa, payee_vpa, amount_paise, status, created_at)
                VALUES (?, ?, ?, ?, 'SUCCESS', ?)
                """).params(id, payer, payee, paise, Timestamp.from(Instant.now())).update();
        return id;
    }

    @Test
    void databaseRejectsTheSameKeyTwiceForOnePayer() {
        String insert = "INSERT INTO idempotency_keys (payer_vpa, idem_key, request_hash) VALUES ('asha@okpaysetu', 'k-0001', ?)";
        jdbc.sql(insert).param("a".repeat(64)).update();

        assertThatThrownBy(() -> jdbc.sql(insert).param("b".repeat(64)).update())
                .isInstanceOf(DuplicateKeyException.class);
    }

    @Test
    void aFailureAfterThePaymentInsertRollsBackTheKeyAndThePayment() {
        doThrow(new IllegalStateException("simulated crash while saving the response"))
                .when(keys).complete(any(), any(), any(), anyInt(), any());

        pay("rollback-key-01", ASHA_PAYS_RAVI).expectStatus().is5xxServerError();

        assertThat(paymentCount()).as("no half-finished payment").isZero();
        assertThat(jdbc.sql("SELECT count(*) FROM idempotency_keys").query(Long.class).single())
                .as("the key is free again").isZero();

        reset(keys);
        pay("rollback-key-01", ASHA_PAYS_RAVI)
                .expectStatus().isCreated()
                .expectHeader().valueEquals("Idempotent-Replayed", "false");
        assertThat(paymentCount()).as("the client's retry succeeds").isEqualTo(1);
    }
}
