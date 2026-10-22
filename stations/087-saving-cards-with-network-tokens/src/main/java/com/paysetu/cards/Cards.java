package com.paysetu.cards;

import org.springframework.dao.DataAccessException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.web.ErrorResponseException;

import java.time.Clock;
import java.time.OffsetDateTime;
import java.time.YearMonth;
import java.time.ZoneId;
import java.util.List;
import java.util.Optional;

@Service
class Cards {

    static final ZoneId IST = ZoneId.of("Asia/Kolkata");

    record SavedCard(long id, String network, String last4, int expiryMonth, int expiryYear) {
    }

    record Payment(long id, String orderId, long savedCardId, long amountPaise, String status, String networkRef) {
    }

    private record Stored(long id, long customerId, String tokenRef, int expiryMonth, int expiryYear, String status) {
    }

    private final JdbcClient jdbc;
    private final SimNetwork network;
    private final Clock clock;

    Cards(JdbcClient jdbc, SimNetwork network, Clock clock) {
        this.jdbc = jdbc;
        this.network = network;
        this.clock = clock;
    }

    /**
     * The card number goes to the network's token service and is then forgotten: it is a parameter here, never a
     * field, a column, a log line or part of an error. Only the token reference and what the customer needs to
     * recognise the card are kept.
     */
    SavedCard save(long customerId, String cardNumber, YearMonth expiry) {
        if (cardNumber.length() < 13 || cardNumber.length() > 19 || !luhn(cardNumber)) {
            throw problem(HttpStatus.BAD_REQUEST, "This is not a valid card number");   // never echo the number
        }
        SimNetwork.Token t;
        try {
            t = network.provision(cardNumber, expiry);
        } catch (SimNetwork.Refused e) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, e.getMessage());
        }
        long id;
        try {
            id = jdbc.sql("""
                            INSERT INTO saved_cards (customer_id, token_ref, network, last4, expiry_month, expiry_year, consent_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id""")
                    .params(customerId, t.tokenRef(), t.network(), t.last4(), expiry.getMonthValue(), expiry.getYear(), OffsetDateTime.now(clock))
                    .query(Long.class).single();
        } catch (DataAccessException e) {
            network.delete(t.tokenRef());   // a token nobody can find again should not stay usable at the network
            throw e;
        }
        return new SavedCard(id, t.network(), t.last4(), expiry.getMonthValue(), expiry.getYear());
    }

    List<SavedCard> list(long customerId) {
        return jdbc.sql("SELECT id, network, last4, expiry_month, expiry_year FROM saved_cards WHERE customer_id = ? AND status = 'active' ORDER BY id")
                .param(customerId).query(SavedCard.class).list();
    }

    /**
     * Pays with a saved card's token and a fresh cryptogram. One payment per order id: the row is written before the
     * network is called, so a retry or a double tap finds it and nothing is charged twice.
     */
    Payment pay(long customerId, long savedCardId, String orderId, long amountPaise) {
        Optional<Payment> earlier = byOrder(customerId, orderId);
        if (earlier.isPresent()) {
            return earlier.get();
        }
        // Someone else's card is "no such card": a 403 would confirm that the id exists.
        Stored card = jdbc.sql("SELECT id, customer_id, token_ref, expiry_month, expiry_year, status FROM saved_cards WHERE id = ? AND customer_id = ? AND status = 'active'")
                .params(savedCardId, customerId).query(Stored.class).optional()
                .orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No such saved card"));
        if (YearMonth.of(card.expiryYear(), card.expiryMonth()).isBefore(YearMonth.now(clock.withZone(IST)))) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "This saved card has expired; save the new card");
        }
        long id;
        try {
            id = jdbc.sql("INSERT INTO payments (customer_id, saved_card_id, order_id, amount_paise, status) VALUES (?, ?, ?, ?, 'pending') RETURNING id")
                    .params(customerId, savedCardId, orderId, amountPaise).query(Long.class).single();
        } catch (DuplicateKeyException e) {
            return byOrder(customerId, orderId).orElseThrow();   // the same order, sent twice at once
        }
        String ref;
        try {
            ref = network.authorise(card.tokenRef(), network.cryptogram(card.tokenRef()), amountPaise);
        } catch (SimNetwork.Refused e) {
            jdbc.sql("UPDATE payments SET status = 'failed' WHERE id = ?").param(id).update();
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, e.getMessage());
        }
        return jdbc.sql("UPDATE payments SET status = ?, network_ref = ? WHERE id = ? RETURNING id, order_id, saved_card_id, amount_paise, status, network_ref")
                .params(ref == null ? "declined" : "succeeded", ref, id).query(Payment.class).single();
    }

    /** An order id belongs to one customer: someone else's is a conflict, never their payment. */
    private Optional<Payment> byOrder(long customerId, String orderId) {
        Optional<Long> owner = jdbc.sql("SELECT customer_id FROM payments WHERE order_id = ?").param(orderId).query(Long.class).optional();
        if (owner.isPresent() && owner.get() != customerId) {
            throw problem(HttpStatus.CONFLICT, "This order id is already used");
        }
        return jdbc.sql("SELECT id, order_id, saved_card_id, amount_paise, status, network_ref FROM payments WHERE order_id = ?")
                .param(orderId).query(Payment.class).optional();
    }

    /** The check digit every card number carries: catches typos before anything is sent to the network. */
    static boolean luhn(String digits) {
        int sum = 0;
        for (int i = 0; i < digits.length(); i++) {
            int d = digits.charAt(digits.length() - 1 - i) - '0';
            if (i % 2 == 1) {
                d = d * 2 > 9 ? d * 2 - 9 : d * 2;
            }
            sum += d;
        }
        return sum % 10 == 0;
    }

    static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }
}
