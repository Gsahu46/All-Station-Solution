package com.billora.invoices;

import java.util.Arrays;
import java.util.Optional;

/**
 * States with their two-digit GST state code, the code e-invoices use for the place of supply. An enum with data:
 * each constant carries its code and name. A demo subset. Challenge 2: union territories charge UTGST instead of SGST.
 */
enum GstState {
    CHANDIGARH("04", "Chandigarh", true),
    DELHI("07", "Delhi", false),
    RAJASTHAN("08", "Rajasthan", false),
    UTTAR_PRADESH("09", "Uttar Pradesh", false),
    WEST_BENGAL("19", "West Bengal", false),
    GUJARAT("24", "Gujarat", false),
    MAHARASHTRA("27", "Maharashtra", false),
    KARNATAKA("29", "Karnataka", false),
    KERALA("32", "Kerala", false),
    TAMIL_NADU("33", "Tamil Nadu", false),
    TELANGANA("36", "Telangana", false);

    final String code;
    final String displayName;
    final boolean unionTerritory;

    GstState(String code, String displayName, boolean unionTerritory) {
        this.code = code;
        this.displayName = displayName;
        this.unionTerritory = unionTerritory;
    }

    static Optional<GstState> byCode(String code) {
        return Arrays.stream(values()).filter(s -> s.code.equals(code)).findFirst();
    }

    /** "29-Karnataka", as printed on an invoice. */
    String label() {
        return code + "-" + displayName;
    }
}
