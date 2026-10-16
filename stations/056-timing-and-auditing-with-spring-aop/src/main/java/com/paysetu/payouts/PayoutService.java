package com.paysetu.payouts;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;

import java.util.Optional;

/** Payouts from a merchant's balance to a bank account. Simulated: a payout record is created; no money moves. */
@Service
class PayoutService {

    record Payout(long id, long merchantId, long amountPaise, String ifsc, String accountLast4, String status) {
    }

    private final JdbcClient jdbc;

    PayoutService(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** No timing or audit code here: the annotation is the whole of it. */
    @Audited(action = "PAYOUT_REQUESTED", subjectParam = "merchantId")
    @Transactional
    public Payout request(long merchantId, long amountPaise, String ifsc, String accountNumber) {
        if (jdbc.sql("SELECT count(*) FROM merchants WHERE id = ?").param(merchantId).query(Long.class).single() == 0) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Unknown merchant", "No merchant " + merchantId + ".");
        }
        int debited = jdbc.sql("UPDATE merchants SET balance_paise = balance_paise - ? WHERE id = ? AND balance_paise >= ?")
                .params(amountPaise, merchantId, amountPaise).update();
        if (debited == 0) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Not enough balance", "Merchant " + merchantId + " cannot pay out " + amountPaise + " paise.");
        }
        String last4 = accountNumber.substring(accountNumber.length() - 4);
        long id = jdbc.sql("INSERT INTO payouts (merchant_id, amount_paise, ifsc, account_last4) VALUES (?, ?, ?, ?) RETURNING id")
                .params(merchantId, amountPaise, ifsc, last4).query(Long.class).single();
        return new Payout(id, merchantId, amountPaise, ifsc, last4, "REQUESTED");
    }

    @Transactional(readOnly = true)
    public Optional<Payout> find(long id) {
        return jdbc.sql("SELECT id, merchant_id, amount_paise, ifsc, account_last4, status FROM payouts WHERE id = ?").param(id).query(Payout.class).optional();
    }

    static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
