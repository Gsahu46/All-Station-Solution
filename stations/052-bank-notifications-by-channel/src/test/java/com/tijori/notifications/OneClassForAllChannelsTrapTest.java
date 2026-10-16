package com.tijori.notifications;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: two changes made for email, in the one class that did all three
 * channels, and what they did to SMS. Then the same debit alert through the fixed service.
 */
class OneClassForAllChannelsTrapTest extends ApiTest {

    final Model.Notice debit = new Model.Notice(Model.NotificationType.DEBIT_ALERT, 149900L, "BIGBASKET", LocalDate.of(2026, 10, 16));

    @Test
    void anEmailChangeStopsTheSmsForCustomersWithoutEmail() throws Exception {
        Model.Customer rohan = customers.find(2).orElseThrow();
        assertThatThrownBy(() -> new OldNotificationService(outbox).notify(rohan, debit)).isInstanceOf(NullPointerException.class);
        assertThat(outbox.all()).isEmpty();   // Rohan's ₹1,499 debit alert never left: no SMS at all

        notify(debit(2, 149900)).andExpect(status().isCreated())
                .andExpect(jsonPath(statusOf("SMS")).value("SENT"))
                .andExpect(jsonPath(statusOf("EMAIL")).value("UNREACHABLE"))
                .andExpect(jsonPath(statusOf("PUSH")).value("SKIPPED"));
    }

    @Test
    void aRupeeSignForEmailTakesTheSmsOutOfGsm7() throws Exception {
        new OldNotificationService(outbox).notify(customers.find(1).orElseThrow(), debit);
        String oldSms = outbox.all().stream().filter(s -> s.channel() == Model.ChannelName.SMS).findFirst().orElseThrow().text();
        assertThat(oldSms).contains("₹").doesNotMatch(GSM7_SUBSET);   // sent as UCS-2: 70 characters a part, so 2 parts
        assertThat(oldSms.length()).isGreaterThan(70);

        outbox.clear();
        notify(debit(1, 149900));
        String sms = outbox.all().stream().filter(s -> s.channel() == Model.ChannelName.SMS).findFirst().orElseThrow().text();
        assertThat(sms).matches(GSM7_SUBSET).hasSizeLessThanOrEqualTo(SmsChannel.MAX_LENGTH);
    }
}
