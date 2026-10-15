package com.mediqo.reminders;

import org.junit.jupiter.api.Test;

import java.text.NumberFormat;
import java.util.Locale;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/** The first test written for this station: it reproduces the bugs before the fix. */
class ConcatenatedReminderTrapTest extends ApiTest {

    /** The "before" bundles: translated fragments, glued together in English word order. Kept only in tests. */
    static final Map<String, Map<String, String>> FRAGMENTS = Map.of(
            "en", Map.of("hello", "Hello ", "with", ", your appointment with Dr ", "on", " is on ", "pay", ". Please pay "),
            "hi", Map.of("hello", "नमस्ते ", "with", ", आपका अपॉइंटमेंट डॉ. ", "on", " के साथ ", "pay", "। कृपया भुगतान करें "));

    static String oldReminder(String lang, String patient, String doctor, String date, long amountPaise) {
        Map<String, String> f = FRAGMENTS.get(lang);
        return f.get("hello") + patient + f.get("with") + doctor + f.get("on") + date + f.get("pay") + (amountPaise / 100.0);
    }

    @Test
    void theOldAmountIsAPlainDoubleAndTheOldDateIsEnglishEverywhere() {
        String hi = oldReminder("hi", "Asha", "Mehta", "20 October 2026", 12_345_650);
        assertThat(hi).endsWith("123456.5");             // no rupee sign, no grouping, one decimal
        assertThat(hi).contains("October");               // the date was formatted once, in English
        assertThat(hi).doesNotContain("को");              // and the Hindi sentence is missing its verb ending: glued, not translated
    }

    @Test
    void javasOwnIndianFormatterGroupsInThrees() {
        // The obvious fix is not enough: DecimalFormat supports one grouping size, so lakhs are missed.
        assertThat(NumberFormat.getCurrencyInstance(Locale.forLanguageTag("en-IN")).format(123_456.50)).isEqualTo("₹123,456.50");
        assertThat(IndianRupees.format(12_345_650)).isEqualTo("₹1,23,456.50");
    }

    @Test
    void theRealReminderIsOneHindiSentenceWithIndianFormatting() throws Exception {
        reminder(501, "hi", null).andExpect(jsonPath("$.text").value(ASHA_HI));
    }
}
