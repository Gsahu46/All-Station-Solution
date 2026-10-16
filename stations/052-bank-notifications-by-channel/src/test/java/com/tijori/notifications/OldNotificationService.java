package com.tijori.notifications;

import java.time.format.DateTimeFormatter;

/**
 * The service as it shipped (900 lines in the original; the parts that matter here), kept only in tests. One class
 * writes and sends all three channels, in order, with one shared amount format.
 */
class OldNotificationService {

    private final Outbox outbox;

    OldNotificationService(Outbox outbox) {
        this.outbox = outbox;
    }

    /** Changed in March for the email redesign: "Rs" became "₹". Every channel uses it. */
    static String amount(long paise) {
        return "₹" + Rupees.format(paise);
    }

    void notify(Model.Customer c, Model.Notice n) {
        // Email first. Also changed in March: the new email provider wants lower-case addresses.
        String email = c.email().toLowerCase();
        outbox.record(Model.ChannelName.EMAIL, email, "Dear " + c.name() + ", " + amount(n.amountPaise()) + " was debited.");
        outbox.record(Model.ChannelName.SMS, c.phone(), "Tijori: " + amount(n.amountPaise()) + " debited from a/c XX" + c.accountLast4()
                + " at " + n.merchant() + " on " + DateTimeFormatter.ofPattern("dd-MM-yy").format(n.date()) + ". Not you? Call 1800-000-0000.");
        if (c.pushToken() != null) {
            outbox.record(Model.ChannelName.PUSH, c.pushToken(), amount(n.amountPaise()) + " debited");
        }
    }
}
