package com.tijori.notifications;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: a fourth channel, WHATSAPP, to the customer's phone number, off unless the customer turns it on
 * ("whatsapp": true in the preferences; absent means false). The notification service should not change at all.
 */
class WhatsAppChallengeTest extends ApiTest {

    @Test
    void whatsAppIsOneMoreChannelClass() throws Exception {
        notify(debit(1, 149900)).andExpect(jsonPath(statusOf("WHATSAPP")).value("SKIPPED"));
        preferences(1, "{\"sms\":true,\"email\":true,\"push\":true,\"whatsapp\":true}").andExpect(status().isOk());
        notify(debit(1, 149900)).andExpect(jsonPath(statusOf("WHATSAPP")).value("SENT"))
                .andExpect(jsonPath("$.deliveries[?(@.channel=='WHATSAPP')].text").value("Tijori: ₹1,499.00 debited from a/c XX4821 at BIGBASKET. Not you? Call 1800-000-0000."));
        notify("{\"customerId\":2,\"type\":\"NEW_DEVICE_LOGIN\"}").andExpect(jsonPath(statusOf("WHATSAPP")).value("SENT"));
    }
}
