package com.fitnest.members;

import java.util.Optional;

/** Indian mobile numbers in one stored form: 10 digits, no spaces, no +91 and no leading 0. */
final class Phones {

    private Phones() {
    }

    static Optional<String> normalise(String raw) {
        String digits = raw.replaceAll("[\\s-]", "");
        if (digits.startsWith("+91")) {
            digits = digits.substring(3);
        } else if (digits.length() == 11 && digits.startsWith("0")) {
            digits = digits.substring(1);
        }
        return digits.matches("[6-9]\\d{9}") ? Optional.of(digits) : Optional.empty();
    }
}
