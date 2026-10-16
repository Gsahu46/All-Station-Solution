package com.tijori.notifications;

/**
 * Paise as Indian-grouped rupees: 12345678 paise is "1,23,456.78". Written by hand because java.text.DecimalFormat
 * supports a single group size, so its en-IN format prints 12,345,678.00 (checked while building this station).
 */
final class Rupees {

    private Rupees() {
    }

    static String format(long paise) {
        String rupees = Long.toString(paise / 100);
        StringBuilder grouped = new StringBuilder(rupees.substring(Math.max(0, rupees.length() - 3)));
        for (int end = rupees.length() - 3; end > 0; end -= 2) {
            grouped.insert(0, rupees.substring(Math.max(0, end - 2), end) + ",");
        }
        return grouped + "." + String.format("%02d", paise % 100);
    }
}
