package com.mediqo.reminders;

import org.junit.jupiter.api.Test;

import java.util.Properties;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 1: Mediqo opens a clinic in Pune. Add Marathi ("mr"): a messages_mr.properties with every key, the same
 * placeholders, and Marathi chosen by ?lang or Accept-Language. Dates use Java's own Marathi month names.
 */
class MarathiChallengeTest extends ApiTest {

    @Test
    void marathiIsChosenByLangOrByTheHeader() throws Exception {
        reminder(501, "mr", null).andExpect(jsonPath("$.language").value("mr"))
                .andExpect(jsonPath("$.text", org.hamcrest.Matchers.allOf(
                        org.hamcrest.Matchers.startsWith("नमस्कार Asha"),
                        org.hamcrest.Matchers.containsString("20 ऑक्टोबर, 2026"),
                        org.hamcrest.Matchers.containsString("₹1,23,456.50"))));
        reminder(502, null, "mr-IN,hi;q=0.8").andExpect(jsonPath("$.language").value("mr"));
    }

    @Test
    void theMarathiBundleHasEveryKeyWithTheSamePlaceholders() throws Exception {
        Properties en = MessagesTest.bundle("messages.properties");
        Properties mr = MessagesTest.bundle("messages_mr.properties");
        assertThat(mr.stringPropertyNames()).containsExactlyInAnyOrderElementsOf(en.stringPropertyNames());
        for (String key : en.stringPropertyNames()) {
            assertThat(MessagesTest.placeholders(mr.getProperty(key))).as(key).isEqualTo(MessagesTest.placeholders(en.getProperty(key)));
        }
    }
}
