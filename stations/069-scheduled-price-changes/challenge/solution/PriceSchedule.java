package com.kartwala.prices;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;

/** Dated prices: a new price never overwrites; it takes its stretch of time, and the neighbours give way. */
@Service
class PriceSchedule {

    record Window(int pricePaise, OffsetDateTime from, OffsetDateTime to) {
    }

    record Schedule(long productId, List<Window> windows) {
    }

    record PriceAt(long productId, OffsetDateTime at, int pricePaise, OffsetDateTime validFrom, OffsetDateTime validTo) {
    }

    private record Row(long id, int pricePaise, Instant validFrom, Instant validTo) {
    }

    private final JdbcClient jdbc;
    private final Clock clock;
    private final ZoneId zone;

    PriceSchedule(JdbcClient jdbc, Clock clock, @Value("${shop.zone}") ZoneId zone) {
        this.jdbc = jdbc;
        this.clock = clock;
        this.zone = zone;
    }

    /** The one price valid at that instant: valid_from <= at < valid_to. The exclusion constraint makes "one" true. */
    PriceAt priceAt(long productId, Instant at) {
        requireProduct(productId);
        return jdbc.sql("""
                        SELECT id, price_paise, valid_from, valid_to FROM prices
                        WHERE product_id = ? AND valid_from <= ? AND (valid_to IS NULL OR valid_to > ?)""")
                .params(productId, utc(at), utc(at)).query(PriceSchedule::row).optional()
                .map(r -> new PriceAt(productId, local(at), r.pricePaise(), local(r.validFrom()), local(r.validTo())))
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Product " + productId + " has no price at " + local(at)));
    }

    /**
     * Sets a price for [from, to) in shop time; to null means "from then on". Rows inside the window go, a row
     * covering its start is cut there, and a row covering its end continues after it.
     */
    @Transactional
    Schedule set(long productId, int pricePaise, LocalDateTime fromLocal, LocalDateTime toLocal) {
        Instant from = fromLocal.atZone(zone).toInstant();
        Instant to = toLocal == null ? null : toLocal.atZone(zone).toInstant();
        if (to != null && !to.isAfter(from)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "The price must end after it starts");
        }
        if (from.isBefore(clock.instant())) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_CONTENT, "Prices in the past are history and cannot change");
        }
        // One schedule change per product at a time: a second one waits here, then sees the first one's rows.
        if (jdbc.sql("SELECT id FROM products WHERE id = ? FOR UPDATE").param(productId).query(Long.class).optional().isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No product " + productId);
        }
        Optional<Row> covering = jdbc.sql("SELECT id, price_paise, valid_from, valid_to FROM prices WHERE product_id = ? AND valid_from < ? AND (valid_to IS NULL OR valid_to > ?)")
                .params(productId, utc(from), utc(from)).query(PriceSchedule::row).optional();
        if (to == null) {
            jdbc.sql("DELETE FROM prices WHERE product_id = ? AND valid_from >= ?").params(productId, utc(from)).update();
        } else {
            jdbc.sql("DELETE FROM prices WHERE product_id = ? AND valid_from >= ? AND valid_to IS NOT NULL AND valid_to <= ?").params(productId, utc(from), utc(to)).update();
            jdbc.sql("UPDATE prices SET valid_from = ? WHERE product_id = ? AND valid_from >= ? AND valid_from < ?").params(utc(to), productId, utc(from), utc(to)).update();
        }
        covering.ifPresent(c -> {
            jdbc.sql("UPDATE prices SET valid_to = ? WHERE id = ?").params(utc(from), c.id()).update();
            if (to != null && (c.validTo() == null || c.validTo().isAfter(to))) {   // the old price resumes after the new window
                insert(productId, c.pricePaise(), to, c.validTo());
            }
        });
        try {
            insert(productId, pricePaise, from, to);
        } catch (DataIntegrityViolationException e) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "The schedule changed meanwhile; read it and try again");
        }
        return schedule(productId);
    }

    /** Challenge 1. */
    Schedule fullSchedule(long productId) {
        requireProduct(productId);
        return schedule(productId);
    }

    /** Challenge 2: remove one future window; the window before it stretches over the gap, and equal neighbours merge. */
    @Transactional
    Schedule cancel(long productId, LocalDateTime fromLocal) {
        Instant from = fromLocal.atZone(zone).toInstant();
        if (jdbc.sql("SELECT id FROM products WHERE id = ? FOR UPDATE").param(productId).query(Long.class).optional().isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No product " + productId);
        }
        Row window = jdbc.sql("SELECT id, price_paise, valid_from, valid_to FROM prices WHERE product_id = ? AND valid_from = ?")
                .params(productId, utc(from)).query(PriceSchedule::row).optional()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No price starts at " + fromLocal));
        if (!window.validFrom().isAfter(clock.instant())) {
            throw new ResponseStatusException(HttpStatus.UNPROCESSABLE_CONTENT, "Prices in the past are history and cannot change");
        }
        jdbc.sql("DELETE FROM prices WHERE id = ?").param(window.id()).update();
        Optional<Row> before = jdbc.sql("SELECT id, price_paise, valid_from, valid_to FROM prices WHERE product_id = ? AND valid_to = ?")
                .params(productId, utc(from)).query(PriceSchedule::row).optional();
        Optional<Row> after = window.validTo() == null ? Optional.empty()
                : jdbc.sql("SELECT id, price_paise, valid_from, valid_to FROM prices WHERE product_id = ? AND valid_from = ?")
                        .params(productId, utc(window.validTo())).query(PriceSchedule::row).optional();
        before.ifPresent(b -> {
            if (after.isPresent() && after.get().pricePaise() == b.pricePaise()) {   // same price on both sides: one window
                jdbc.sql("DELETE FROM prices WHERE id = ?").param(after.get().id()).update();
                jdbc.sql("UPDATE prices SET valid_to = ? WHERE id = ?").params(utc(after.get().validTo()), b.id()).update();
            } else {
                jdbc.sql("UPDATE prices SET valid_to = ? WHERE id = ?").params(utc(window.validTo()), b.id()).update();
            }
        });
        return schedule(productId);
    }

    Schedule schedule(long productId) {
        List<Window> windows = jdbc.sql("SELECT id, price_paise, valid_from, valid_to FROM prices WHERE product_id = ? ORDER BY valid_from")
                .param(productId).query(PriceSchedule::row).list().stream()
                .map(r -> new Window(r.pricePaise(), local(r.validFrom()), local(r.validTo()))).toList();
        return new Schedule(productId, windows);
    }

    private void insert(long productId, int pricePaise, Instant from, Instant to) {
        jdbc.sql("INSERT INTO prices (product_id, price_paise, valid_from, valid_to) VALUES (?, ?, ?, ?)")
                .params(productId, pricePaise, utc(from), utc(to)).update();
    }

    private void requireProduct(long productId) {
        if (jdbc.sql("SELECT count(*) FROM products WHERE id = ?").param(productId).query(Long.class).single() == 0) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No product " + productId);
        }
    }

    private OffsetDateTime local(Instant instant) {
        return instant == null ? null : instant.atZone(zone).toOffsetDateTime();
    }

    /** Bound as an offset date-time, so PostgreSQL never interprets it in the server's or session's time zone. */
    private static OffsetDateTime utc(Instant instant) {
        return instant == null ? null : instant.atOffset(ZoneOffset.UTC);
    }

    private static Row row(java.sql.ResultSet rs, int i) throws java.sql.SQLException {
        OffsetDateTime to = rs.getObject("valid_to", OffsetDateTime.class);
        return new Row(rs.getLong("id"), rs.getInt("price_paise"), rs.getObject("valid_from", OffsetDateTime.class).toInstant(), to == null ? null : to.toInstant());
    }
}
