package com.tijori.passkeys;

import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;
import tools.jackson.databind.node.ObjectNode;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The rules hold for every writer, not only this app: plain SQL straight to PostgreSQL, no Java checks on the way. */
class PasskeyDatabaseTest extends ApiTest {

    void violates(String constraint, String sql) {
        assertThatThrownBy(() -> jdbc.sql(sql).update()).isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining(constraint);
    }

    static final String ZOYA = "(SELECT id FROM customers WHERE email = 'zoya@example.com')";

    @Test
    void challengeRulesHoldWithoutJava() {
        violates("webauthn_challenges_length", "INSERT INTO webauthn_challenges (challenge, purpose, created_at, expires_at) VALUES ('\\x0102', 'authentication', now(), now() + interval '1 minute')");
        violates("webauthn_challenges_purpose", "INSERT INTO webauthn_challenges (challenge, purpose, created_at, expires_at) VALUES (gen_random_bytes(32), 'payment', now(), now() + interval '1 minute')");
        violates("webauthn_challenges_registration_has_customer", "INSERT INTO webauthn_challenges (challenge, purpose, created_at, expires_at) VALUES (gen_random_bytes(32), 'registration', now(), now() + interval '1 minute')");
        violates("webauthn_challenges_expiry", "INSERT INTO webauthn_challenges (challenge, purpose, created_at, expires_at) VALUES (gen_random_bytes(32), 'authentication', now(), now() + interval '1 day')");
        violates("webauthn_challenges_used_in_time", "INSERT INTO webauthn_challenges (challenge, purpose, created_at, expires_at, used_at) VALUES (gen_random_bytes(32), 'authentication', now(), now() + interval '1 minute', now() - interval '1 hour')");
    }

    @Test
    void passkeyAndCustomerRulesHoldWithoutJava() {
        String passkey = "INSERT INTO passkeys (credential_id, customer_id, attested_credential_data, sign_count, label, created_at) VALUES ";
        violates("passkeys_credential_id_length", passkey + "('\\x01', " + ZOYA + ", '\\x00', 0, 'Phone', now())");
        violates("passkeys_sign_count_range", passkey + "(gen_random_bytes(16), " + ZOYA + ", '\\x00', -1, 'Phone', now())");
        violates("passkeys_label_length", passkey + "(gen_random_bytes(16), " + ZOYA + ", '\\x00', 0, '', now())");
        violates("customers_user_handle_length", "UPDATE customers SET user_handle = 'zoya@example.com' WHERE email = 'zoya@example.com'");
        violates("customers_totp_secret_length", "UPDATE customers SET totp_secret = '\\x0102' WHERE email = 'zoya@example.com'");
        violates("customers_balance_nonnegative", "UPDATE customers SET balance_paise = -1 WHERE email = 'zoya@example.com'");
        violates("customers_email_lower", "UPDATE customers SET email = 'Zoya@Example.com' WHERE email = 'zoya@example.com'");
    }

    /**
     * Registration is one transaction. If the passkey cannot be saved, the challenge is not used up either, so the
     * customer's phone can send the same answer again. (A failed check, by contrast, does use it up: see Security.)
     */
    @Test
    void aSaveThatFailsRollsBackAndTheSameAnswerCanBeSentAgain() throws Exception {
        String token = codeToken("zoya");
        ObjectNode answer = new Device().create(registrationOptions(token));
        jdbc.sql("""
                CREATE FUNCTION refuse_passkeys() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'storage is down'; END $$ LANGUAGE plpgsql;
                CREATE TRIGGER refuse_passkeys BEFORE INSERT ON passkeys FOR EACH ROW EXECUTE FUNCTION refuse_passkeys()""").update();
        try {
            assertThatThrownBy(() -> register(token, "Zoya's phone", answer)).hasRootCauseMessage("ERROR: storage is down\n  Where: PL/pgSQL function refuse_passkeys() line 1 at RAISE");
        } finally {
            jdbc.sql("DROP TRIGGER refuse_passkeys ON passkeys; DROP FUNCTION refuse_passkeys()").update();
        }
        assertThat(jdbc.sql("SELECT count(*) FROM webauthn_challenges WHERE used_at IS NULL").query(Long.class).single()).isEqualTo(1);
        register(token, "Zoya's phone", answer).andExpect(status().isCreated());
    }

    @Test
    void aFailedCheckUsesUpTheChallenge() throws Exception {
        String token = codeToken("zoya");
        Device phone = new Device();
        ObjectNode forOtherSite = phone.create(registrationOptions(token), "tijori-login.example");
        register(token, "Zoya's phone", forOtherSite).andExpect(status().isBadRequest());
        assertThat(jdbc.sql("SELECT count(*) FROM webauthn_challenges WHERE used_at IS NULL").query(Long.class).single()).isZero();
    }
}
