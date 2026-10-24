package com.taskloom.support;

import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Removes personal data before a thread leaves Taskloom. Catches the formats below and the customer's own name; it does
 * not catch everything (an address, another person's name, a number spelled out), so it lowers the risk, it does not
 * remove it.
 */
final class Redactor {

    record Redacted(String text, Map<String, Integer> removed) {
    }

    private static final Pattern EMAIL = Pattern.compile("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}");
    // 13 to 19 digits, spaces or dashes between them; only numbers that pass the Luhn check count as cards.
    private static final Pattern CARD = Pattern.compile("(?<!\\d)(?:\\d[ -]?){12,18}\\d(?!\\d)");
    private static final Pattern AADHAAR = Pattern.compile("(?<!\\d)\\d{4}[ -]?\\d{4}[ -]?\\d{4}(?!\\d)");
    // Indian mobile numbers: +91 or 0 optional, then 10 digits starting 6 to 9.
    private static final Pattern PHONE = Pattern.compile("(?<![\\d+])(?:\\+91[ -]?|0)?[6-9]\\d{4}[ -]?\\d{5}(?!\\d)");
    private static final Pattern PAN = Pattern.compile("\\b[A-Za-z]{5}\\d{4}[A-Za-z]\\b");

    private Redactor() {
    }

    static Redacted redact(String text, String customerName) {
        Map<String, Integer> removed = new TreeMap<>();
        text = replace(text, EMAIL, "[EMAIL]", "email", removed, false);
        text = replace(text, CARD, "[CARD]", "card", removed, true);
        text = replace(text, AADHAAR, "[AADHAAR]", "aadhaar", removed, false);
        text = replace(text, PHONE, "[PHONE]", "phone", removed, false);
        text = replace(text, PAN, "[PAN]", "pan", removed, false);
        for (String part : customerName.split("\\s+")) {
            if (part.length() >= 3) {
                text = replace(text, Pattern.compile("\\b" + Pattern.quote(part) + "\\b", Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE),
                        "[CUSTOMER]", "name", removed, false);
            }
        }
        return new Redacted(text, removed);
    }

    private static String replace(String text, Pattern pattern, String label, String kind, Map<String, Integer> removed, boolean luhn) {
        Matcher m = pattern.matcher(text);
        StringBuilder out = new StringBuilder();
        while (m.find()) {
            if (luhn && !luhn(m.group().replaceAll("[ -]", ""))) {
                continue;
            }
            m.appendReplacement(out, Matcher.quoteReplacement(label));
            removed.merge(kind.toLowerCase(Locale.ROOT), 1, Integer::sum);
        }
        m.appendTail(out);
        return out.toString();
    }

    static boolean luhn(String digits) {
        int sum = 0;
        for (int i = 0; i < digits.length(); i++) {
            int d = digits.charAt(digits.length() - 1 - i) - '0';
            sum += i % 2 == 1 ? (d * 2 > 9 ? d * 2 - 9 : d * 2) : d;
        }
        return sum % 10 == 0;
    }
}
