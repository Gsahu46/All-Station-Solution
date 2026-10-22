package com.seatsure.holds;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataAccessException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.sql.SQLException;
import java.time.Clock;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
class Holds {

    record Hold(UUID id, long showId, String customer, List<String> seatNos, long totalPaise, OffsetDateTime expiresAt, String status, String paymentRef) {
    }

    /** The seat is being locked by someone else for longer than we are willing to wait. */
    static final class SeatBusy extends RuntimeException {
    }

    private record Seat(String seatNo, long pricePaise, boolean free) {
    }

    private final JdbcClient jdbc;
    private final TransactionTemplate tx;
    private final Payments payments;
    private final Clock clock;
    private final Duration holdFor;
    private final long lockTimeoutMs;

    Holds(JdbcClient jdbc, TransactionTemplate tx, Payments payments, Clock clock,
          @Value("${seatsure.hold-for}") Duration holdFor, @Value("${seatsure.lock-timeout}") Duration lockTimeout) {
        this.jdbc = jdbc;
        this.tx = tx;
        this.payments = payments;
        this.clock = clock;
        this.holdFor = holdFor;
        this.lockTimeoutMs = lockTimeout.toMillis();
    }

    /**
     * Holds these seats, all or none. The seat rows are locked (SELECT ... FOR UPDATE) for the few milliseconds of
     * this transaction only, and never waited on for longer than the lock timeout.
     */
    Hold hold(long showId, String customer, List<String> seatNos) {
        return inSeatTransaction(() -> {
            OffsetDateTime now = now();
            List<Seat> seats = jdbc.sql("""
                            SELECT seat_no, price_paise, booked_by IS NULL AND (hold_id IS NULL OR held_until <= ?) AS free
                            FROM seats WHERE show_id = ? AND seat_no = ANY(?) ORDER BY seat_no FOR UPDATE""")
                    .params(now, showId, seatNos.toArray(String[]::new)).query(Seat.class).list();
            if (seats.size() != seatNos.size()) {
                throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No such show or seat");
            }
            if (!seats.stream().allMatch(Seat::free)) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "Taken: " + String.join(", ", seats.stream().filter(s -> !s.free()).map(Seat::seatNo).toList()));
            }
            return save(showId, customer, seats, now);
        });
    }

    /**
     * Any n free seats. FOR UPDATE SKIP LOCKED: seats someone is locking right now are passed over instead of
     * waited for, so ten people asking at once get ten different pairs.
     */
    Hold holdAny(long showId, String customer, int count) {
        return inSeatTransaction(() -> {
            OffsetDateTime now = now();
            List<Seat> seats = jdbc.sql("""
                            SELECT seat_no, price_paise, true AS free FROM seats
                            WHERE show_id = ? AND booked_by IS NULL AND (hold_id IS NULL OR held_until <= ?)
                            ORDER BY seat_no LIMIT ? FOR UPDATE SKIP LOCKED""")
                    .params(showId, now, count).query(Seat.class).list();
            if (seats.size() < count) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "Not enough free seats");
            }
            return save(showId, customer, seats, now);
        });
    }

    private Hold save(long showId, String customer, List<Seat> seats, OffsetDateTime now) {
        UUID id = UUID.randomUUID();
        OffsetDateTime until = now.plus(holdFor);
        List<String> nos = seats.stream().map(Seat::seatNo).toList();
        long total = seats.stream().mapToLong(Seat::pricePaise).sum();
        jdbc.sql("UPDATE seats SET hold_id = ?, held_until = ? WHERE show_id = ? AND seat_no = ANY(?)").params(id, until, showId, nos.toArray(String[]::new)).update();
        jdbc.sql("INSERT INTO holds (id, show_id, customer, seat_nos, total_paise, expires_at, status) VALUES (?, ?, ?, ?, ?, ?, 'held')")
                .params(id, showId, customer, nos.toArray(String[]::new), total, until).update();
        return new Hold(id, showId, customer, nos, total, until, "held", null);
    }

    /**
     * Payment first, with no lock held: the provider may take seconds. Then one short statement books the seats if
     * this hold still owns them. If they were taken after the hold ran out, the payment is refunded (simulated); a
     * hold that ran out while paying but whose seats nobody took still books.
     */
    Hold confirm(UUID holdId) {
        Hold hold = find(holdId).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No such hold"));
        if (!hold.status().equals("held")) {
            return hold;   // confirming twice answers the same: a retry after a timeout is safe
        }
        if (!hold.expiresAt().isAfter(now())) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "This hold has expired");
        }
        String paymentRef = payments.charge(holdId.toString(), hold.totalPaise());
        Boolean booked = tx.execute(s -> {
            // Still this hold's seats? If someone else held them after this hold ran out, hold_id has changed.
            int rows = jdbc.sql("UPDATE seats SET booked_by = ?, hold_id = NULL, held_until = NULL WHERE hold_id = ?")
                    .params(hold.customer(), holdId).update();
            if (rows != hold.seatNos().size()) {
                s.setRollbackOnly();
                return false;
            }
            jdbc.sql("UPDATE holds SET status = 'confirmed', payment_ref = ? WHERE id = ?").params(paymentRef, holdId).update();
            return true;
        });
        if (!Boolean.TRUE.equals(booked)) {
            payments.refund(holdId.toString());
            jdbc.sql("UPDATE holds SET status = 'refunded', payment_ref = ? WHERE id = ?").params(paymentRef, holdId).update();
            throw new ResponseStatusException(HttpStatus.CONFLICT, "The hold ran out while paying; the payment was refunded");
        }
        return find(holdId).orElseThrow();
    }

    /** The seats go back at once; a confirmed or finished hold stays as it is. */
    void release(UUID holdId) {
        tx.executeWithoutResult(s -> {
            String status = jdbc.sql("SELECT status FROM holds WHERE id = ? FOR UPDATE").param(holdId).query(String.class).optional()
                    .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "No such hold"));
            if (!status.equals("held")) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "This hold is " + status);
            }
            jdbc.sql("UPDATE seats SET hold_id = NULL, held_until = NULL WHERE hold_id = ?").param(holdId).update();
            jdbc.sql("UPDATE holds SET status = 'released' WHERE id = ?").param(holdId).update();
        });
    }

    Optional<Hold> find(UUID holdId) {
        return jdbc.sql("SELECT id, show_id, customer, seat_nos, total_paise, expires_at, status, payment_ref FROM holds WHERE id = ?").param(holdId)
                .query((rs, n) -> new Hold(rs.getObject(1, UUID.class), rs.getLong(2), rs.getString(3), List.of((String[]) rs.getArray(4).getArray()),
                        rs.getLong(5), rs.getObject(6, OffsetDateTime.class), rs.getString(7), rs.getString(8))).optional();
    }

    private <T> T inSeatTransaction(java.util.function.Supplier<T> work) {
        try {
            return tx.execute(s -> {
                // Never wait forever for a seat: give up after the lock timeout and let the customer try again.
                jdbc.sql("SELECT set_config('lock_timeout', ?, true)").param(lockTimeoutMs + "ms").query(String.class).single();
                return work.get();
            });
        } catch (DataAccessException e) {
            // PostgreSQL's lock timeout is SQLState 55P03; Spring 7 reports it as UncategorizedSQLException, so match the state.
            if (e.getMostSpecificCause() instanceof SQLException sql && "55P03".equals(sql.getSQLState())) {
                throw new SeatBusy();
            }
            throw e;
        }
    }

    private OffsetDateTime now() {
        // PostgreSQL keeps microseconds: without this, the expiresAt we answer differs from the one we stored.
        return OffsetDateTime.ofInstant(clock.instant().truncatedTo(ChronoUnit.MICROS), ZoneOffset.UTC);
    }
}
