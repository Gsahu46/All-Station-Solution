package com.tijori.notifications;

import org.springframework.stereotype.Component;

/** WhatsApp: to the phone number, Unicode allowed, so "₹" is fine. A new class; nothing else had to change. */
@Component
class WhatsAppChannel implements Channel {

    private final Outbox outbox;

    WhatsAppChannel(Outbox outbox) {
        this.outbox = outbox;
    }

    @Override
    public Model.ChannelName name() {
        return Model.ChannelName.WHATSAPP;
    }

    @Override
    public Model.Delivery deliver(Model.Customer c, Model.Notice n) {
        if (c.phone() == null) {
            return new Model.Delivery(name(), Model.Status.UNREACHABLE, null, null);
        }
        String text = switch (n.type()) {
            case DEBIT_ALERT -> "Tijori: ₹" + Rupees.format(n.amountPaise()) + " debited from a/c XX" + c.accountLast4()
                    + (n.merchant() == null ? "" : " at " + n.merchant()) + ". Not you? Call 1800-000-0000.";
            case NEW_DEVICE_LOGIN -> "Tijori: a new device just logged in to your account. Not you? Call 1800-000-0000.";
            case STATEMENT_READY -> "Tijori: your statement is ready in the app.";
        };
        outbox.record(name(), c.phone(), text);
        return new Model.Delivery(name(), Model.Status.SENT, "******" + c.phone().substring(6), text);
    }
}
