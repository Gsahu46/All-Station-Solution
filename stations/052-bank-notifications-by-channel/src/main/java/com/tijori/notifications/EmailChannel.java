package com.tijori.notifications;

import org.springframework.stereotype.Component;

import java.time.format.DateTimeFormatter;
import java.util.Locale;

/** Email: a subject line and a longer, friendlier body. "₹" is fine here. */
@Component
class EmailChannel implements Channel {

    private static final DateTimeFormatter DATE = DateTimeFormatter.ofPattern("d MMMM yyyy", Locale.ENGLISH);

    private final Outbox outbox;

    EmailChannel(Outbox outbox) {
        this.outbox = outbox;
    }

    @Override
    public Model.ChannelName name() {
        return Model.ChannelName.EMAIL;
    }

    @Override
    public Model.Delivery deliver(Model.Customer c, Model.Notice n) {
        if (c.email() == null) {
            return new Model.Delivery(name(), Model.Status.UNREACHABLE, null, null);
        }
        String text = switch (n.type()) {
            case DEBIT_ALERT -> "Subject: ₹" + Rupees.format(n.amountPaise()) + " debited\n\nDear " + c.name() + ",\n₹" + Rupees.format(n.amountPaise())
                    + " was debited from your account ending " + c.accountLast4() + (n.merchant() == null ? "" : " at " + n.merchant())
                    + " on " + DATE.format(n.date()) + ".";
            case NEW_DEVICE_LOGIN -> "Subject: New login to Tijori\n\nDear " + c.name() + ",\nYour account was opened on a new device on " + DATE.format(n.date()) + ".";
            case STATEMENT_READY -> "Subject: Your statement is ready\n\nDear " + c.name() + ",\nYour statement for the account ending " + c.accountLast4() + " is ready.";
        };
        String to = c.email().toLowerCase(Locale.ROOT);
        outbox.record(name(), to, text);
        return new Model.Delivery(name(), Model.Status.SENT, to.charAt(0) + "***" + to.substring(to.indexOf('@')), text);
    }
}
