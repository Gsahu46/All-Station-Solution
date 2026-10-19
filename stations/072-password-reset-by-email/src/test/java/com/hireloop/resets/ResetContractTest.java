package com.hireloop.resets;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class ResetContractTest extends ApiTest {

    @Test
    void theWholeResetFromRequestToNewPassword() throws Exception {
        requestReset("Priya@Example.com").andExpect(status().isAccepted())
                .andExpect(jsonPath("$.message").value("If an account exists for this email, we have sent a link to reset its password."));
        assertThat(emailsTo("priya@example.com")).isEqualTo(1);
        complete(linkTokenFor("priya@example.com"), "priya-new-long-password").andExpect(status().isNoContent());
        me("priya@example.com", "priya-old-password").andExpect(status().isUnauthorized());
        me("priya@example.com", "priya-new-long-password").andExpect(status().isOk()).andExpect(jsonPath("$.fullName").value("Priya Nair"));
    }

    @Test
    void anUnknownEmailGetsTheSameReplyAndNoEmail() throws Exception {
        requestReset("nobody@example.com").andExpect(status().isAccepted())
                .andExpect(jsonPath("$.message").value("If an account exists for this email, we have sent a link to reset its password."));
        assertThat(jdbc.sql("SELECT count(*) FROM outbox_emails").query(Long.class).single()).isZero();
    }

    @Test
    void anUnknownLinkIs400() throws Exception {
        complete("A".repeat(43), "a-new-long-password").andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("This link is invalid or has expired; ask for a new one"));
    }

    @Test
    void badRequestsAre400() throws Exception {
        requestReset("not-an-email").andExpect(status().isBadRequest());
        requestReset("priya@example.com");
        complete(linkTokenFor("priya@example.com"), "short").andExpect(status().isBadRequest());
        complete(linkTokenFor("priya@example.com"), "₹".repeat(30)).andExpect(status().isBadRequest());   // 90 bytes
        me("priya@example.com", "priya-old-password").andExpect(status().isOk());   // nothing changed, and the link still works
        complete(linkTokenFor("priya@example.com"), "a-good-new-password").andExpect(status().isNoContent());
    }
}
