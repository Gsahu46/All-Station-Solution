package com.chaupal.comments;

import org.springframework.stereotype.Component;

import java.util.Set;

/** Simple and fast: lower-case the text and look for each banned word. */
@Component
class Moderation {

    static final Set<String> BANNED = Set.of("idiot", "stupid", "scam");

    boolean breaksRules(String text) {
        String lower = text.toLowerCase();
        return BANNED.stream().anyMatch(lower::contains);
    }

    static java.util.List<String> words(String text) {
        return java.util.List.of(text.toLowerCase().split("\\s+"));
    }
}
