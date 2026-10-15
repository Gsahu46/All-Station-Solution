package com.tiffino.orders;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Component;

import java.util.Optional;

/**
 * PR: "Drop the sequence: numbers follow on from the last order, so there are no gaps and support can count orders
 * from them. Simpler check digit. Lookups take the number exactly as stored."
 */
@Component
class OrderNumbers {

    private final JdbcClient jdbc;

    OrderNumbers(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    String next() {
        long value = jdbc.sql("SELECT coalesce(max(substring(order_number from 4 for 7)::bigint), 1000000) + 1 FROM orders")
                .query(Long.class).single();
        String digits = Long.toString(value);
        return "TF-" + digits + "-" + checkDigit(digits);
    }

    /** The sum of the digits, last digit. */
    static int checkDigit(String digits) {
        int sum = 0;
        for (int i = 0; i < digits.length(); i++) {
            sum += digits.charAt(i) - '0';
        }
        return sum % 10;
    }

    static Optional<String> normalise(String raw) {
        String compact = raw.replaceAll("[\\s-]", "");
        if (!compact.matches("TF\\d{8}")) {
            return Optional.empty();
        }
        return Optional.of("TF-" + compact.substring(2, 9) + "-" + compact.charAt(9));
    }

    static boolean checkDigitMatches(String number) {
        return checkDigit(number.substring(3, 10)) == number.charAt(11) - '0';
    }
}
