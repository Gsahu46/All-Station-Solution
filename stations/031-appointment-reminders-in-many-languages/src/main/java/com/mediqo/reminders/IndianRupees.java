package com.mediqo.reminders;

/**
 * Paise as Indian rupees: "₹1,23,456.50". The last three digits form one group, then groups of two (lakh, crore).
 * Java's NumberFormat for en-IN gets the symbol right but groups in threes (₹123,456.50): DecimalFormat supports
 * only one grouping size. So this small method does the grouping itself.
 */
final class IndianRupees {

    private IndianRupees() {
    }

    static String format(long paise) {
        if (paise < 0) {
            throw new IllegalArgumentException("amounts in reminders are never negative");
        }
        String rupees = Long.toString(paise / 100);
        String decimals = "." + String.format("%02d", paise % 100);
        if (rupees.length() <= 3) {
            return "₹" + rupees + decimals;
        }
        String head = rupees.substring(0, rupees.length() - 3);   // everything before the last three digits
        StringBuilder grouped = new StringBuilder();
        for (int i = 0; i < head.length(); i++) {
            if (i > 0 && (head.length() - i) % 2 == 0) {
                grouped.append(',');                              // a comma before every pair, counted from the right
            }
            grouped.append(head.charAt(i));
        }
        return "₹" + grouped + "," + rupees.substring(rupees.length() - 3) + decimals;
    }
}
