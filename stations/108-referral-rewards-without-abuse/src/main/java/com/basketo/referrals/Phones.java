package com.basketo.referrals;

import java.util.Optional;

/** Indian mobile numbers in one form, +91 and ten digits, so "098123 45670" and "+91 98123-45670" are one person. */
final class Phones {

    private Phones() {
    }

    static Optional<String> normalise(String raw) {
        if (raw == null) {
            return Optional.empty();
        }
        String digits = raw.replaceAll("[\\s-]", "");
        if (digits.startsWith("+91")) {
            digits = digits.substring(3);
        } else if (digits.length() == 12 && digits.startsWith("91")) {
            digits = digits.substring(2);
        } else if (digits.length() == 11 && digits.startsWith("0")) {
            digits = digits.substring(1);
        }
        return digits.matches("[6-9]\\d{9}") ? Optional.of("+91" + digits) : Optional.empty();
    }
}
