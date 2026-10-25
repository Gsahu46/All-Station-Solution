package com.chaupal.accounts;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Lazy;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.json.JsonMapper;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

/** Data exports and account deletion, both as background jobs. */
@Service
class Accounts {

    record Export(long id, String status, Instant requestedAt, Instant readyAt) {
    }

    record Deletion(String status, Instant dueBy) {
    }

    private static final Logger log = LoggerFactory.getLogger(Accounts.class);
    // What a person gets in their export: their own data. Others' address books that hold their number are not theirs.
    private static final Map<String, String> EXPORTED = new LinkedHashMap<>();

    static {
        EXPORTED.put("account", "SELECT name, phone, email FROM users WHERE id = :user");
        EXPORTED.put("profile", "SELECT bio, city, date_of_birth FROM profiles WHERE user_id = :user");
        EXPORTED.put("posts", "SELECT id, body, created_at FROM posts WHERE user_id = :user ORDER BY id");
        EXPORTED.put("comments", "SELECT id, post_id, body, created_at FROM comments WHERE user_id = :user ORDER BY id");
        EXPORTED.put("contactsYouUploaded", "SELECT contact_name, contact_phone FROM contact_uploads WHERE uploader_id = :user ORDER BY id");
        EXPORTED.put("invoices", "SELECT id, buyer_name, buyer_phone, amount_paise, issued_on FROM invoices WHERE user_id = :user ORDER BY id");
        EXPORTED.put("signIns", "SELECT ip, at FROM login_events WHERE user_id = :user ORDER BY at");
        EXPORTED.put("supportTickets", "SELECT id, message FROM support_tickets WHERE user_id = :user ORDER BY id");
    }

    private final JdbcClient jdbc;
    private final JsonMapper json;
    private final Accounts self;   // through the proxy, so erase() runs in its own transaction

    Accounts(JdbcClient jdbc, JsonMapper json, @Lazy Accounts self) {
        this.jdbc = jdbc;
        this.json = json;
        this.self = self;
    }

    long idOf(String login) {
        return jdbc.sql("SELECT id FROM users WHERE login = ?").param(login).query(Long.class).single();
    }

    Export requestExport(long user) {
        long id = jdbc.sql("INSERT INTO data_exports (user_id) VALUES (?) RETURNING id").param(user).query(Long.class).single();
        return export(user, id).orElseThrow();
    }

    /** Another person's export is not found, the same as one that does not exist. */
    Optional<Export> export(long user, long id) {
        return jdbc.sql("SELECT id, status, requested_at, ready_at FROM data_exports WHERE id = ? AND user_id = ?").params(id, user)
                .query(Export.class).optional();
    }

    /** An export is downloadable for 7 days after it is ready. */
    private static final String EXPIRED = "ready_at < now() - interval '7 days'";

    Optional<String> exportFile(long user, long id) {
        return jdbc.sql("SELECT content::text FROM data_exports WHERE id = ? AND user_id = ? AND status = 'READY' AND NOT (" + EXPIRED + ")")
                .params(id, user).query(String.class).optional();
    }

    boolean expired(long user, long id) {
        return jdbc.sql("SELECT count(*) FROM data_exports WHERE id = ? AND user_id = ? AND (status = 'EXPIRED' OR " + EXPIRED + ")")
                .params(id, user).query(Integer.class).single() > 0;
    }

    /** Signs the person out for good (status is no longer ACTIVE) and books the erasure, due within 90 days. */
    @Transactional
    Deletion requestDeletion(long user) {
        jdbc.sql("UPDATE users SET status = 'DELETION_REQUESTED', deletion_requested_at = now() WHERE id = ? AND status = 'ACTIVE'").param(user).update();
        jdbc.sql("INSERT INTO erasures (user_id, requested_at, due_by) VALUES (?, now(), now() + interval '90 days') ON CONFLICT DO NOTHING").param(user).update();
        return jdbc.sql("SELECT u.status, e.due_by FROM users u JOIN erasures e ON e.user_id = u.id WHERE u.id = ?").param(user).query(Deletion.class).single();
    }

    @Scheduled(fixedDelayString = "${chaupal.jobs.every}")
    void runJobs() {
        jdbc.sql("SELECT id, user_id FROM data_exports WHERE status = 'PENDING' ORDER BY id")
                .query((rs, n) -> new long[]{rs.getLong(1), rs.getLong(2)}).list().forEach(e -> buildExport(e[0], e[1]));
        // The copy inside an expired export is personal data too: emptied, not kept.
        jdbc.sql("UPDATE data_exports SET status = 'EXPIRED', content = NULL WHERE status = 'READY' AND " + EXPIRED).update();
        for (long user : jdbc.sql("SELECT id FROM users WHERE status = 'DELETION_REQUESTED' ORDER BY id").query(Long.class).list()) {
            try {
                self.erase(user);
            } catch (RuntimeException e) {
                // One account that cannot be erased must not hold up the others; it is tried again next time.
                log.error("Erasure of account {} failed and was rolled back: {}", user, e.getMessage());
            }
        }
    }

    void buildExport(long id, long user) {
        Map<String, Object> content = new LinkedHashMap<>();
        EXPORTED.forEach((name, sql) -> content.put(name, jdbc.sql(sql).param("user", user).query().listOfRows()));
        jdbc.sql("UPDATE data_exports SET status = 'READY', content = ?::jsonb, ready_at = now() WHERE id = ? AND status = 'PENDING'")
                .params(json.writeValueAsString(content), id).update();
    }

    /** Every entry of the inventory, in order, in one transaction: all of it is erased, or none of it. */
    @Transactional
    void erase(long user) {
        String phone = jdbc.sql("SELECT phone FROM users WHERE id = ?").param(user).query(String.class).single();
        for (PersonalData.Entry entry : PersonalData.INVENTORY) {
            if (entry.sql() != null) {
                var statement = jdbc.sql(entry.sql()).param("user", user);
                if (entry.sql().contains(":phone")) {
                    statement = statement.param("phone", phone);
                }
                statement.update();
            }
        }
        jdbc.sql("UPDATE erasures SET completed_at = now() WHERE user_id = ?").param(user).update();
        log.info("Account {} erased", user);   // the id only: logs are not a place for the data being erased
    }

    /**
     * Accounts with no sign-in for three years: one notice, then, 48 hours later and still no sign-in, the erasure is
     * booked. A sign-in after the notice cancels it.
     */
    void sweepInactive() {
        String lastSeen = "(SELECT max(at) FROM login_events l WHERE l.user_id = u.id)";
        jdbc.sql("UPDATE users u SET inactivity_notice_at = NULL WHERE inactivity_notice_at IS NOT NULL AND " + lastSeen + " > inactivity_notice_at").update();
        jdbc.sql("SELECT id FROM users u WHERE status = 'ACTIVE' AND role = 'MEMBER' AND inactivity_notice_at < now() - interval '48 hours'")
                .query(Long.class).list().forEach(this::requestDeletion);
        jdbc.sql("WITH quiet AS (UPDATE users u SET inactivity_notice_at = now() WHERE status = 'ACTIVE' AND role = 'MEMBER' "
                + "AND inactivity_notice_at IS NULL AND coalesce(" + lastSeen + ", '-infinity') < now() - interval '3 years' RETURNING phone) "
                + "INSERT INTO notification_outbox (phone, text) SELECT phone, "
                + "'Your Chaupal account has not been used for 3 years and will be erased in 48 hours unless you sign in.' FROM quiet").update();
    }

    /** Sign-in records older than 180 days, for everyone. */
    @Scheduled(cron = "${chaupal.jobs.purge-cron}")
    void purgeLoginEvents() {
        jdbc.sql("DELETE FROM login_events WHERE at < now() - interval '180 days'").update();
    }
}
