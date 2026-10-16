package com.tijori.notifications;

import org.springframework.stereotype.Component;

/** Push: a short line for the lock screen. No account digits on a lock screen. */
@Component
class PushChannel implements Channel {

    private final Outbox outbox;

    PushChannel(Outbox outbox) {
        this.outbox = outbox;
    }

    @Override
    public Model.ChannelName name() {
        return Model.ChannelName.PUSH;
    }

    @Override
    public Model.Delivery deliver(Model.Customer c, Model.Notice n) {
        if (c.pushToken() == null) {
            return new Model.Delivery(name(), Model.Status.UNREACHABLE, null, null);
        }
        String text = switch (n.type()) {
            case DEBIT_ALERT -> "₹" + Rupees.format(n.amountPaise()) + " debited" + (n.merchant() == null ? "" : " at " + n.merchant());
            case NEW_DEVICE_LOGIN -> "New login to your Tijori account";
            case STATEMENT_READY -> "Your statement is ready";
        };
        outbox.record(name(), c.pushToken(), text);
        return new Model.Delivery(name(), Model.Status.SENT, "this customer's app", text);
    }
}
