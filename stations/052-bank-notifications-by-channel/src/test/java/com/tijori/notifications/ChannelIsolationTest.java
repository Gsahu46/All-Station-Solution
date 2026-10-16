package com.tijori.notifications;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.bean.override.mockito.MockitoSpyBean;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** A channel that breaks, and money formatting on its own: each part tested without the others. */
class ChannelIsolationTest extends ApiTest {

    @MockitoSpyBean
    EmailChannel email;

    @Test
    void anEmailOutageLeavesSmsAndPushWorking() throws Exception {
        doThrow(new IllegalStateException("email provider timed out")).when(email).deliver(any(), any());
        notify(debit(1, 149900)).andExpect(status().isCreated())
                .andExpect(jsonPath(statusOf("SMS")).value("SENT")).andExpect(jsonPath(statusOf("EMAIL")).value("FAILED")).andExpect(jsonPath(statusOf("PUSH")).value("SENT"));
        assertThat(outbox.all()).extracting(Outbox.Sent::channel).containsExactlyInAnyOrder(Model.ChannelName.SMS, Model.ChannelName.PUSH);
    }

    @Test
    void rupeesAreGroupedInThreeThenTwos() {
        assertThat(Rupees.format(0)).isEqualTo("0.00");
        assertThat(Rupees.format(5)).isEqualTo("0.05");
        assertThat(Rupees.format(99_999)).isEqualTo("999.99");
        assertThat(Rupees.format(100_000)).isEqualTo("1,000.00");
        assertThat(Rupees.format(10_000_000)).isEqualTo("1,00,000.00");      // one lakh
        assertThat(Rupees.format(1_000_000_000L)).isEqualTo("1,00,00,000.00"); // one crore
    }
}
