package com.billora.invoices;

import org.springframework.stereotype.Component;

import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Simulated: demo invoices INV-2026-0001 to INV-2026-0500, where invoice n has n pages. INV-2026-0013 has a broken
 * logo, so rendering it fails (to show a failed job).
 */
@Component
class Invoices {

    record Invoice(String id, int pages) {
    }

    static final Pattern ID = Pattern.compile("INV-2026-(\\d{4})");

    Optional<Invoice> find(String id) {
        Matcher m = ID.matcher(id);
        if (!m.matches()) {
            return Optional.empty();
        }
        int n = Integer.parseInt(m.group(1));
        return n >= 1 && n <= 500 ? Optional.of(new Invoice(id, n)) : Optional.empty();
    }
}
