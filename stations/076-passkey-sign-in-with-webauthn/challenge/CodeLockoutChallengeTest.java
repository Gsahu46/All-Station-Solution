package com.tijori.passkeys;

import org.junit.jupiter.api.Test;

import java.time.Duration;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: a six-digit code has a million values. After 5 wrong codes in a row (with the right password), code
 * sign-in is locked for 15 minutes: even the right code is refused with the same 401. A good sign-in resets the count.
 */
class CodeLockoutChallengeTest extends ApiTest {

    @org.junit.jupiter.api.BeforeEach
    void noFailedCodes() {
        jdbc.sql("UPDATE customers SET failed_codes = 0, codes_locked_until = NULL").update();   // other tests may have tried a wrong code
    }

    static String wrong(String right) {
        return right.equals("000000") ? "111111" : "000000";
    }

    @Test
    void fiveWrongCodesLockCodeSignInForFifteenMinutes() throws Exception {
        for (int i = 0; i < 5; i++) {
            codeSignIn("dev@example.com", "dev-demo-pass", wrong(currentCode())).andExpect(status().isUnauthorized());
        }
        codeSignIn("dev@example.com", "dev-demo-pass", currentCode()).andExpect(status().isUnauthorized());
        later(Duration.ofMinutes(15).plusSeconds(1));
        codeSignIn("dev@example.com", "dev-demo-pass", currentCode()).andExpect(status().isOk());
    }

    @Test
    void aGoodSignInResetsTheCount() throws Exception {
        for (int i = 0; i < 4; i++) {
            codeSignIn("dev@example.com", "dev-demo-pass", wrong(currentCode())).andExpect(status().isUnauthorized());
        }
        codeSignIn("dev@example.com", "dev-demo-pass", currentCode()).andExpect(status().isOk());
        later(Duration.ofSeconds(30));
        codeSignIn("dev@example.com", "dev-demo-pass", wrong(currentCode())).andExpect(status().isUnauthorized());
        codeSignIn("dev@example.com", "dev-demo-pass", currentCode()).andExpect(status().isOk());
    }
}
