package com.billora.invoices;

import java.util.Arrays;
import java.util.Optional;

/**
 * States with their two-digit GST state code, the code e-invoices use for the place of supply. An enum with data:
 * each constant carries its code and name. A demo subset; union territories are left out (they charge UTGST, not SGST).
 */
enum GstState {
    DELHI("07", "Delhi"),
    RAJASTHAN("08", "Rajasthan"),
    UTTAR_PRADESH("09", "Uttar Pradesh"),
    WEST_BENGAL("19", "West Bengal"),
    GUJARAT("24", "Gujarat"),
    MAHARASHTRA("27", "Maharashtra"),
    KARNATAKA("29", "Karnataka"),
    KERALA("32", "Kerala"),
    TAMIL_NADU("33", "Tamil Nadu"),
    TELANGANA("36", "Telangana");

    final String code;
    final String displayName;

    GstState(String code, String displayName) {
        this.code = code;
        this.displayName = displayName;
    }

    static Optional<GstState> byCode(String code) {
        return Arrays.stream(values()).filter(s -> s.code.equals(code)).findFirst();
    }

    /** "29-Karnataka", as printed on an invoice. */
    String label() {
        return code + "-" + displayName;
    }
}
