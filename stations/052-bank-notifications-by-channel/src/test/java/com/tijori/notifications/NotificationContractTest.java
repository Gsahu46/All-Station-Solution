package com.tijori.notifications;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The HTTP contract: notices per channel and preferences; valid, invalid and not found. */
class NotificationContractTest extends ApiTest {

    @Test
    void aDebitAlertGoesToEveryChannelInItsOwnWords() throws Exception {
        String sms = "$.deliveries[?(@.channel=='SMS')]", email = "$.deliveries[?(@.channel=='EMAIL')]", push = "$.deliveries[?(@.channel=='PUSH')]";
        notify(debit(1, 149900)).andExpect(status().isCreated())
                .andExpect(jsonPath("$.customerId").value(1)).andExpect(jsonPath("$.type").value("DEBIT_ALERT"))
                .andExpect(jsonPath(sms + ".to").value("******3210"))
                .andExpect(jsonPath(sms + ".text").value("Tijori: Rs 1,499.00 debited from a/c XX4821 at BIGBASKET on 16-10-26. Not you? Call 1800-000-0000."))
                .andExpect(jsonPath(email + ".to").value("a***@example.in"))
                .andExpect(jsonPath(email + ".text").value(org.hamcrest.Matchers.hasItem(org.hamcrest.Matchers.startsWith("Subject: ₹1,499.00 debited"))))
                .andExpect(jsonPath(push + ".text").value("₹1,499.00 debited at BIGBASKET"));
        assertThat(outbox.all()).hasSize(3);
    }

    @Test
    void preferencesDecideExceptWhereTheRulesSayOtherwise() throws Exception {
        preferences(1, "{\"sms\":false,\"email\":false,\"push\":true}").andExpect(status().isOk())
                .andExpect(content().json("{\"sms\":false,\"email\":false,\"push\":true}"));
        notify("{\"customerId\":1,\"type\":\"STATEMENT_READY\"}")   // preferences only
                .andExpect(jsonPath(statusOf("SMS")).value("SKIPPED")).andExpect(jsonPath(statusOf("EMAIL")).value("SKIPPED")).andExpect(jsonPath(statusOf("PUSH")).value("SENT"));
        notify(debit(1, 149900))                                    // SMS always, the rest by preference
                .andExpect(jsonPath(statusOf("SMS")).value("SENT")).andExpect(jsonPath(statusOf("EMAIL")).value("SKIPPED")).andExpect(jsonPath(statusOf("PUSH")).value("SENT"));
        notify("{\"customerId\":1,\"type\":\"NEW_DEVICE_LOGIN\"}")  // every channel
                .andExpect(jsonPath(statusOf("SMS")).value("SENT")).andExpect(jsonPath(statusOf("EMAIL")).value("SENT")).andExpect(jsonPath(statusOf("PUSH")).value("SENT"));
    }

    @Test
    void lakhsAndCroresAreGroupedTheIndianWay() throws Exception {
        notify(debit(1, 12_345_678_90L)).andExpect(jsonPath("$.deliveries[?(@.channel=='SMS')].text")
                .value("Tijori: Rs 1,23,45,678.90 debited from a/c XX4821 at BIGBASKET on 16-10-26. Not you? Call 1800-000-0000."));
    }

    @Test
    void brokenRequestsAre400() throws Exception {
        notify("{\"type\":\"DEBIT_ALERT\",\"amountPaise\":100}").andExpect(status().isBadRequest());
        notify("{\"customerId\":1,\"type\":\"LOAN_OFFER\"}").andExpect(status().isBadRequest());
        notify(debit(1, 0)).andExpect(status().isBadRequest());
        notify(debit(1, 149900).replace("149900", "1499.50")).andExpect(status().isBadRequest());
        notify(debit(1, 149900).replace("BigBasket", "Big Basket Super Saver Store")).andExpect(status().isBadRequest());   // over 24
        preferences(1, "{\"sms\":true,\"email\":true}").andExpect(status().isBadRequest());
        assertThat(outbox.all()).isEmpty();
    }

    @Test
    void impossibleNoticesAre422() throws Exception {
        notify("{\"customerId\":1,\"type\":\"DEBIT_ALERT\"}").andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Amount missing"));
        notify(debit(99, 149900)).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Unknown customer"));
    }

    @Test
    void unknownCustomersPreferencesAre404() throws Exception {
        preferences(99, "{\"sms\":true,\"email\":true,\"push\":true}").andExpect(status().isNotFound())
                .andExpect(jsonPath("$.detail").value("No customer 99."));
    }
}
