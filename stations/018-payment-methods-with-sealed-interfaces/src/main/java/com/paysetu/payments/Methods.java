package com.paysetu.payments;

import com.paysetu.payments.PaymentMethod.Card;
import com.paysetu.payments.PaymentMethod.NetBanking;
import com.paysetu.payments.PaymentMethod.Upi;
import com.paysetu.payments.PaymentMethod.Wallet;

/**
 * Everything that differs by payment method, as switches over the sealed interface. No default branch on purpose:
 * the compiler proves each switch handles every method. Simulated: no UPI app, bank or card network is contacted.
 */
final class Methods {

    record NextAction(String type, String detail) {
    }

    private Methods() {
    }

    static NextAction nextAction(PaymentMethod method, String amount) {
        return switch (method) {
            case Upi(String vpa) -> new NextAction("APPROVE_IN_UPI_APP",
                    "Approve " + amount + " to Paysetu in the UPI app linked to " + vpa + ".");
            case Card(Card.Network network, String last4, String token) -> new NextAction("AUTHENTICATE_CARD",
                    "Enter the one-time password from your bank for the " + network + " card ending " + last4 + ".");
            case NetBanking(String bankCode) -> new NextAction("REDIRECT_TO_BANK",
                    "/simulated-banks/" + bankCode + "/login");
            case Wallet w -> new NextAction("CONFIRM_WALLET_DEBIT",
                    "Confirm the " + amount + " debit in the Paysetu wallet of " + w.maskedMobile() + ".");
        };
    }

    /** Where a refund of this payment goes. The old code's version of this forgot wallets. */
    static String refundRoute(PaymentMethod method) {
        return switch (method) {
            case Upi(String vpa) -> "Back to the bank account behind the UPI ID " + vpa + ".";
            case Card(Card.Network network, String last4, String token) -> "Back to the " + network + " card ending " + last4 + ".";
            case NetBanking(String bankCode) -> "Back to the account at bank " + bankCode + " it was paid from.";
            case Wallet w -> "Back to the Paysetu wallet of " + w.maskedMobile() + ".";
        };
    }
}
