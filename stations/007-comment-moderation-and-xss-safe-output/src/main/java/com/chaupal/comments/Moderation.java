package com.chaupal.comments;

import org.springframework.stereotype.Component;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * Finds banned words after normalising the text, so the usual disguises still match:
 * "ＩＤＩＯＴ" (full-width letters), "1d10t" and "$c@m" (look-alike digits and symbols), "s c a m" (spaced out),
 * "stuuupid" (stretched). It compares whole words, so "scampi" is not "scam".
 * A word list is a first line of defence, never the only one: people invent new spellings every day.
 */
@Component
class Moderation {

    static final Set<String> BANNED = Set.of("idiot", "stupid", "scam");

    boolean breaksRules(String text) {
        return words(text).stream().anyMatch(BANNED::contains);
    }

    /** The text as normalised words. Package-private so tests can show each step. */
    static List<String> words(String text) {
        String t = Normalizer.normalize(text, Normalizer.Form.NFKC).toLowerCase(Locale.ROOT); // ＩＤＩＯＴ -> idiot
        StringBuilder mapped = new StringBuilder();
        for (char c : t.toCharArray()) {
            mapped.append(switch (c) {
                case '0' -> 'o';
                case '1' -> 'i';
                case '3' -> 'e';
                case '4', '@' -> 'a';
                case '5', '$' -> 's';
                case '7' -> 't';
                default -> c;
            });
        }
        List<String> words = new ArrayList<>();
        StringBuilder run = new StringBuilder(); // consecutive one-letter words: "s c a m" -> "scam"
        for (String token : mapped.toString().split("\\s+")) {
            String w = token.replaceAll("[^\\p{L}]", "").replaceAll("(\\p{L})\\1{2,}", "$1"); // letters only; "uuu" -> "u"
            if (w.length() == 1) {
                run.append(w);
                continue;
            }
            if (!run.isEmpty()) {
                words.add(run.toString());
                run.setLength(0);
            }
            if (!w.isEmpty()) {
                words.add(w);
            }
        }
        if (!run.isEmpty()) {
            words.add(run.toString());
        }
        return words;
    }
}
