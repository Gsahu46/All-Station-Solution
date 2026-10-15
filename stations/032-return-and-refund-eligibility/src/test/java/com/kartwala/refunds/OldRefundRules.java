package com.kartwala.refunds;

/**
 * The window rule as it was before the fix, kept only in tests. Clothing and electronics shared one case of a switch.
 * In March electronics moved from 30 days to 7: the change was made in the shared case, so clothing moved too.
 */
final class OldRefundRules {

    private OldRefundRules() {
    }

    static int windowDays(Category category) {
        switch (category) {
            case CLOTHING:
            case ELECTRONICS:
                return 7;   // was 30 for both; "electronics only" was the intent
            case BOOKS:
                return 10;
            default:
                return 2;
        }
    }

    static boolean withinWindow(Category category, int daysSinceDelivery) {
        return daysSinceDelivery <= windowDays(category);
    }
}
