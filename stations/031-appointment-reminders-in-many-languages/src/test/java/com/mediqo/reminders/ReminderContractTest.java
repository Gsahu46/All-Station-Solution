package com.mediqo.reminders;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.MessageSource;
import org.springframework.http.MediaType;

import java.util.Locale;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: how the language is chosen, the fallback, and every refusal. */
class ReminderContractTest extends ApiTest {

    @Test
    void theLangParameterWins() throws Exception {
        reminder(501, "en", "hi-IN").andExpect(status().isOk())
                .andExpect(jsonPath("$.language").value("en"))
                .andExpect(jsonPath("$.text").value(ASHA_EN));
    }

    @Test
    void withoutLangTheAcceptLanguageHeaderDecides() throws Exception {
        reminder(502, null, "hi-IN,hi;q=0.9,en;q=0.8").andExpect(jsonPath("$.language").value("hi"))
                .andExpect(jsonPath("$.text").value("नमस्ते Ravi, डॉ. Iyer के साथ आपका अपॉइंटमेंट 21 अक्टूबर 2026 को 15:00 बजे है। कृपया क्लिनिक में ₹500.00 का भुगतान करें।"));
    }

    @Test
    void withNeitherThePatientsPreferenceDecides() throws Exception {
        reminder(501, null, null).andExpect(jsonPath("$.language").value("hi")).andExpect(jsonPath("$.text").value(ASHA_HI));
        reminder(502, null, null).andExpect(jsonPath("$.language").value("en"));
    }

    @Test
    void aLanguageWeDoNotHaveFallsBackToEnglish() throws Exception {
        reminder(501, "ta", null).andExpect(status().isOk())
                .andExpect(jsonPath("$.language").value("en"))
                .andExpect(jsonPath("$.requestedLanguage").value("ta"))
                .andExpect(jsonPath("$.text").value(ASHA_EN));
        reminder(501, null, "ta-IN,ml;q=0.5").andExpect(jsonPath("$.language").value("en"));
    }

    @Test
    void anUnknownAppointmentIs404AndAMalformedLangIs400() throws Exception {
        reminder(999, "hi", null).andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Appointment not found"));
        reminder(501, "<script>", null).andExpect(status().isBadRequest());
        reminder(501, "hindi-language", null).andExpect(status().isBadRequest());
    }

    @Autowired
    MessageSource messages;

    @Test
    void theServersOwnLocaleNeverDecidesTheFallback() {
        // A server whose JVM runs in Hindi. French is used because no other test asks for it, so no bundle is cached.
        Locale before = Locale.getDefault();
        Locale.setDefault(Locale.forLanguageTag("hi-IN"));
        try {
            String text = messages.getMessage("reminder.text", new Object[]{"A", "B", "C", "D", "E"}, Locale.FRENCH);
            assertThat(text).startsWith("Hello A");
        } finally {
            Locale.setDefault(before);
        }
    }
}
