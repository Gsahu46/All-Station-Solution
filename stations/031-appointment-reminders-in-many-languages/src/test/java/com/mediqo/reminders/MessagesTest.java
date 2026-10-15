package com.mediqo.reminders;

import org.junit.jupiter.api.Test;

import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Properties;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.assertj.core.api.Assertions.assertThat;

/** The bundles and the formatter on their own: every key translated, the same placeholders, and Indian grouping. */
class MessagesTest {

    static Properties bundle(String name) throws Exception {
        Properties p = new Properties();
        try (var in = new InputStreamReader(MessagesTest.class.getResourceAsStream("/" + name), StandardCharsets.UTF_8)) {
            p.load(in);
        }
        return p;
    }

    static TreeSet<String> placeholders(String text) {
        TreeSet<String> found = new TreeSet<>();
        Matcher m = Pattern.compile("\\{\\d+}").matcher(text);
        while (m.find()) {
            found.add(m.group());
        }
        return found;
    }

    @Test
    void everyEnglishMessageHasAHindiOneWithTheSamePlaceholders() throws Exception {
        Properties en = bundle("messages.properties");
        Properties hi = bundle("messages_hi.properties");
        assertThat(hi.stringPropertyNames()).containsExactlyInAnyOrderElementsOf(en.stringPropertyNames());
        for (String key : en.stringPropertyNames()) {
            assertThat(placeholders(hi.getProperty(key))).as(key).isEqualTo(placeholders(en.getProperty(key)));
        }
    }

    @Test
    void rupeesAreGroupedInLakhsAndCrores() {
        assertThat(IndianRupees.format(0)).isEqualTo("₹0.00");
        assertThat(IndianRupees.format(5)).isEqualTo("₹0.05");
        assertThat(IndianRupees.format(99_999)).isEqualTo("₹999.99");
        assertThat(IndianRupees.format(100_000)).isEqualTo("₹1,000.00");
        assertThat(IndianRupees.format(10_000_000)).isEqualTo("₹1,00,000.00");
        assertThat(IndianRupees.format(12_345_650)).isEqualTo("₹1,23,456.50");
        assertThat(IndianRupees.format(1_234_567_890)).isEqualTo("₹1,23,45,678.90");
        assertThat(IndianRupees.format(10_000_000_000L)).isEqualTo("₹10,00,00,000.00");
    }

    @Test
    void languageMatchingFollowsAcceptLanguageRules() {
        assertThat(ReminderController.choose("hi-IN").getLanguage()).isEqualTo("hi");
        assertThat(ReminderController.choose("ta,hi;q=0.5").getLanguage()).isEqualTo("hi");   // the best one we have
        assertThat(ReminderController.choose("ta").getLanguage()).isEqualTo("en");
        assertThat(ReminderController.choose("not a header;;q=x").getLanguage()).isEqualTo("en");
    }
}
