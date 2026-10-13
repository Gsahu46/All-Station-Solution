package com.chaupal.comments;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.util.Locale;

import static org.assertj.core.api.Assertions.assertThat;

/** Moderation on its own: the disguises it sees through, and the innocent words it must leave alone. */
class ModerationTest {

    private final Moderation moderation = new Moderation();
    private final Locale original = Locale.getDefault();

    @AfterEach
    void restoreLocale() {
        Locale.setDefault(original);
    }

    @Test
    void disguisesAreSeenThrough() {
        for (String text : new String[]{"you idiot", "IDIOT!", "ＩＤＩＯＴ", "1d10t", "$c@m alert", "s c a m", "so stuuupid", "id-iot"}) {
            assertThat(moderation.breaksRules(text)).as(text).isTrue();
        }
    }

    @Test
    void wholeWordsOnlySoScampiIsFine() {
        for (String text : new String[]{"Try the scampi", "Scampi fry at Mahesh Lunch Home", "That was a smart idea"}) {
            assertThat(moderation.breaksRules(text)).as(text).isFalse();
        }
    }

    @Test
    void theLimitsOfAWordList() {
        // Honest limits: a different form of the word, or a mask character, gets through. Moderators still matter.
        assertThat(moderation.breaksRules("stupidity")).isFalse();
        assertThat(moderation.breaksRules("st*pid")).isFalse();
    }

    @Test
    void stepsAreVisible() {
        assertThat(Moderation.words("Ｓ c a m, 1d10t!!")).containsExactly("scam", "idiot");
    }

    @Test
    void aTurkishServerLocaleChangesNothing() {
        Locale.setDefault(Locale.forLanguageTag("tr-TR")); // "IDIOT".toLowerCase() would be "ıdıot"
        assertThat(moderation.breaksRules("IDIOT")).isTrue();
    }
}
