package com.tijori.notifications;

import org.springframework.stereotype.Component;

import java.time.format.DateTimeFormatter;

/**
 * SMS: one part of 160 characters in the GSM-7 alphabet. "₹" is not in GSM-7: one ₹ makes the whole message UCS-2,
 * where a part holds only 70 characters. So SMS says "Rs", and only this class has to know that.
 */
@Component
class SmsChannel implements Channel {

    static final int MAX_LENGTH = 160;
    private static final DateTimeFormatter DATE = DateTimeFormatter.ofPattern("dd-MM-yy");

    private final Outbox outbox;

    SmsChannel(Outbox outbox) {
        this.outbox = outbox;
    }

    @Override
    public Model.ChannelName name() {
        return Model.ChannelName.SMS;
    }

    @Override
    public Model.Delivery deliver(Model.Customer c, Model.Notice n) {
        if (c.phone() == null) {
            return new Model.Delivery(name(), Model.Status.UNREACHABLE, null, null);
        }
        String text = switch (n.type()) {
            case DEBIT_ALERT -> "Tijori: Rs " + Rupees.format(n.amountPaise()) + " debited from a/c XX" + c.accountLast4()
                    + (n.merchant() == null ? "" : " at " + n.merchant()) + " on " + DATE.format(n.date()) + ". Not you? Call 1800-000-0000.";
            case NEW_DEVICE_LOGIN -> "Tijori: new login to your account on " + DATE.format(n.date()) + ". Not you? Call 1800-000-0000.";
            case STATEMENT_READY -> "Tijori: your statement for a/c XX" + c.accountLast4() + " is ready in the app.";
        };
        if (text.length() > MAX_LENGTH) {
            throw new IllegalStateException("SMS over " + MAX_LENGTH + " characters: " + text.length());
        }
        outbox.record(name(), c.phone(), text);
        return new Model.Delivery(name(), Model.Status.SENT, "******" + c.phone().substring(6), text);
    }
}
