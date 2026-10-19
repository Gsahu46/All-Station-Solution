package com.hireloop.resets;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Security: 401, 403, a link can only change its own account, malicious input, and one link used twice at once. */
class ResetSecurityTest extends ApiTest {

    @Test
    void theProfileNeedsCredentials401() throws Exception {
        mvc.perform(get("/candidates/me")).andExpect(status().isUnauthorized());
        me("priya@example.com", "not-her-password").andExpect(status().isUnauthorized());
    }

    @Test
    void aSuspendedAccountIs403AndGetsNoLink() throws Exception {
        me("kiran@example.com", "kiran-old-password").andExpect(status().isForbidden());
        requestReset("kiran@example.com").andExpect(status().isAccepted());   // the same reply as everyone
        assertThat(emailsTo("kiran@example.com")).isZero();
    }

    @Test
    void aLinkChangesOnlyTheAccountItWasSentFor() throws Exception {
        requestReset("priya@example.com");
        complete(linkTokenFor("priya@example.com"), "priya-new-long-password").andExpect(status().isNoContent());
        me("arjun@example.com", "arjun-old-password").andExpect(status().isOk());   // nothing in the request names an account
        me("arjun@example.com", "priya-new-long-password").andExpect(status().isUnauthorized());
    }

    @Test
    void aNewPasswordCancelsEveryOtherOpenLink() throws Exception {
        requestReset("priya@example.com");
        String first = linkTokenFor("priya@example.com");
        requestReset("priya@example.com");
        String second = linkTokenFor("priya@example.com");
        complete(second, "priya-new-long-password").andExpect(status().isNoContent());
        complete(first, "an-attacker-password").andExpect(status().isBadRequest());   // an older email in a stolen inbox is useless now
    }

    @Test
    void floodingTheFormSendsAtMostThreeLinks() throws Exception {
        for (int i = 0; i < 10; i++) {
            requestReset("priya@example.com").andExpect(status().isAccepted());
        }
        assertThat(emailsTo("priya@example.com")).isEqualTo(PasswordResets.MAX_OPEN_LINKS);
    }

    @Test
    void oddTokensAreJustUnknownLinks() throws Exception {
        complete("x' OR '1'='1", "a-new-long-password").andExpect(status().isBadRequest());
        complete("A".repeat(500), "a-new-long-password").andExpect(status().isBadRequest());
        complete("..%2F..%2Fadmin", "a-new-long-password").andExpect(status().isBadRequest());
    }

    @Test
    void oneLinkUsedTwiceAtTheSameMomentWorksOnce() throws Exception {
        requestReset("priya@example.com");
        String token = linkTokenFor("priya@example.com");
        CountDownLatch start = new CountDownLatch(1);
        List<Future<Integer>> results = new ArrayList<>();
        try (ExecutorService threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 10; i++) {
                String password = "parallel-password-" + i;
                results.add(threads.submit(() -> {
                    start.await();
                    return complete(token, password).andReturn().getResponse().getStatus();
                }));
            }
            start.countDown();
        }
        List<Integer> statuses = new ArrayList<>();
        for (Future<Integer> f : results) {
            statuses.add(f.get());
        }
        assertThat(statuses).containsOnly(204, 400);
        assertThat(statuses).filteredOn(s -> s == 204).hasSize(1);
    }
}
