package com.chaupal.accounts;

import java.util.List;

/**
 * The personal data inventory: every table, what in it points at a person, and what happens to it when they delete
 * their account. PersonalDataInventoryTest compares this list with the database, so a new table cannot be forgotten.
 * The SQL runs in order, in one transaction, with :user (the account's id) and :phone (its number).
 */
final class PersonalData {

    enum Action { DELETE, KEEP_FOR_LAW, ANONYMISE, NONE }

    record Entry(String table, String findsBy, Action action, String why, String sql) {
    }

    static final List<Entry> INVENTORY = List.of(
            new Entry("profiles", "user_id", Action.DELETE, "Bio, city, date of birth.",
                    "DELETE FROM profiles WHERE user_id = :user"),
            new Entry("comments", "user_id", Action.DELETE, "Their comments; others' comments under their posts go with the posts.",
                    "DELETE FROM comments WHERE user_id = :user"),
            new Entry("posts", "user_id", Action.DELETE, "Their posts, which can hold anything, phone numbers included.",
                    "DELETE FROM posts WHERE user_id = :user"),
            new Entry("otp_requests", "phone", Action.DELETE, "Keyed by phone: a delete by user id misses them.",
                    "DELETE FROM otp_requests WHERE phone = :phone"),
            new Entry("contact_uploads", "uploader_id, contact_phone", Action.DELETE,
                    "Their own address book, and their number in other members' uploads.",
                    "DELETE FROM contact_uploads WHERE uploader_id = :user OR contact_phone = :phone"),
            new Entry("support_tickets", "user_id, phone", Action.DELETE, "Their tickets, by account or by the number they wrote from.",
                    "DELETE FROM support_tickets WHERE user_id = :user OR phone = :phone"),
            new Entry("notification_outbox", "phone", Action.DELETE, "Messages not yet sent to them.",
                    "DELETE FROM notification_outbox WHERE phone = :phone"),
            new Entry("data_exports", "user_id", Action.DELETE, "Copies of their data made earlier.",
                    "DELETE FROM data_exports WHERE user_id = :user"),
            new Entry("login_events", "user_id", Action.KEEP_FOR_LAW,
                    "Kept 180 days for security; older ones go now, the rest when LoginEventPurge reaches them.",
                    "DELETE FROM login_events WHERE user_id = :user AND at < now() - interval '180 days'"),
            new Entry("invoices", "user_id, buyer_phone", Action.KEEP_FOR_LAW,
                    "Tax invoices must be kept until retain_until, deletion request or not; not shown to anyone but finance.", null),
            new Entry("users", "id", Action.ANONYMISE, "The row stays so that kept records still point somewhere; nothing in it identifies the person.",
                    "UPDATE users SET login = NULL, password_hash = NULL, name = NULL, phone = NULL, email = NULL, "
                            + "status = 'DELETED', deleted_at = now() WHERE id = :user"),
            new Entry("erasures", "user_id", Action.NONE, "The record that an erasure was asked for and done: no personal data.", null),
            new Entry("flyway_schema_history", "-", Action.NONE, "Migrations.", null));

    private PersonalData() {
    }
}
