package com.tijori.notifications;

import java.time.LocalDate;

/** The few plain types every part shares. No behaviour lives here. */
final class Model {

    private Model() {
    }

    enum ChannelName { SMS, EMAIL, PUSH, WHATSAPP }

    enum Status { SENT, SKIPPED, UNREACHABLE, FAILED }

    /**
     * Who gets what, by type. Demo rules: a debit alert always goes by SMS; a new-device login goes to every channel
     * we can reach; a statement notice follows the customer's preferences only.
     */
    enum NotificationType {
        DEBIT_ALERT, NEW_DEVICE_LOGIN, STATEMENT_READY;

        boolean wants(ChannelName channel, Preferences p) {
            return switch (this) {
                case NEW_DEVICE_LOGIN -> true;
                case DEBIT_ALERT -> channel == ChannelName.SMS || p.allows(channel);
                case STATEMENT_READY -> p.allows(channel);
            };
        }
    }

    record Preferences(boolean sms, boolean email, boolean push, boolean whatsapp) {
        Preferences(boolean sms, boolean email, boolean push) {
            this(sms, email, push, false);   // WhatsApp is opt-in
        }

        boolean allows(ChannelName channel) {
            return switch (channel) {   // the compiler lists every place a new channel must be decided
                case SMS -> sms;
                case EMAIL -> email;
                case PUSH -> push;
                case WHATSAPP -> whatsapp;
            };
        }
    }

    /** Any of phone, email and pushToken may be missing: not every customer has an app or an email address. */
    record Customer(long id, String name, String accountLast4, String phone, String email, String pushToken) {
    }

    /** What happened, without any channel's wording. Each channel writes its own text from this. */
    record Notice(NotificationType type, Long amountPaise, String merchant, LocalDate date) {
    }

    record Delivery(ChannelName channel, Status status, String to, String text) {
    }
}
