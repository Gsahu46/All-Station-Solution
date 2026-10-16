package com.taskloom.welcome;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

import java.time.Duration;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.timeout;
import static org.mockito.Mockito.verify;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** A CRM that hangs: the sign-up must not wait for it, and the welcome email must not wait for it either. */
class SlowCrmTest extends ApiTest {

    @MockitoBean
    CrmClient crm;

    @Test
    void theSignupAndTheEmailDoNotWaitForTheCrm() throws Exception {
        CountDownLatch crmAnswers = new CountDownLatch(1);
        doAnswer(call -> {
            crmAnswers.await(3, TimeUnit.SECONDS);   // the CRM hangs until the test lets it go (at most 3 s)
            return null;
        }).when(crm).register(anyLong(), anyString(), anyString());

        long start = System.nanoTime();
        signUp("asha@x.com", "Asha Verma", null).andExpect(status().isCreated());
        assertThat(Duration.ofNanos(System.nanoTime() - start)).isLessThan(Duration.ofSeconds(2));   // answered while the CRM hangs
        eventually(() -> assertThat(mailbox.all()).hasSize(1));                     // and welcomed while it hangs
        verify(crm, timeout(2000)).register(1L, "asha@x.com", "Asha Verma");
        crmAnswers.countDown();
    }
}
