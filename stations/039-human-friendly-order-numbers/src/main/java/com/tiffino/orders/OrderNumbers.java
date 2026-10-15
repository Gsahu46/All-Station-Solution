package com.tiffino.orders;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.util.Locale;
import java.util.Optional;

/**
 * Order numbers a customer can read out on the phone: "TF-1000427-3". Seven digits from the database sequence, then a
 * Luhn check digit, which catches any single wrong digit and most swapped neighbours before we even look the order up.
 */
@Component
class OrderNumbers {

    private final JdbcClient jdbc;

    OrderNumbers(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    String next() {
        long value = jdbc.sql("SELECT nextval('order_number_seq')").query(Long.class).single();
        String digits = Long.toString(value);
        return "TF-" + digits + "-" + checkDigit(digits);
    }

    /** Luhn (ISO/IEC 7812-1, the digit on payment cards): double every second digit from the right, sum, round up to 10. */
    static int checkDigit(String digits) {
        int sum = 0;
        boolean twice = true;   // the rightmost payload digit is doubled, since the check digit will sit to its right
        for (int i = digits.length() - 1; i >= 0; i--) {
            int d = digits.charAt(i) - '0';
            if (twice) {
                d *= 2;
                if (d > 9) {
                    d -= 9;
                }
            }
            sum += d;
            twice = !twice;
        }
        return (10 - sum % 10) % 10;
    }

    /** "tf 1000427 3", "TF10004273" and "TF-1000427-3" are the same number. Empty if it is not shaped like one. */
    static Optional<String> normalise(String raw) {
        String compact = raw.replaceAll("[\\s-]", "").toUpperCase(Locale.ROOT);
        if (!compact.matches("TF\\d{8}")) {
            return Optional.empty();
        }
        return Optional.of("TF-" + compact.substring(2, 9) + "-" + compact.charAt(9));
    }

    static boolean checkDigitMatches(String number) {
        return checkDigit(number.substring(3, 10)) == number.charAt(11) - '0';
    }
}
