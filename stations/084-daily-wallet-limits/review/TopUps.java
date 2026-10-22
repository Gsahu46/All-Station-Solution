package com.tijori.wallets;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.Locale;

@Service
class TopUps {

    /** Daily limits reset at midnight in India, not at midnight UTC (05:30 IST). */
    static final ZoneId IST = ZoneId.of("Asia/Kolkata");

    record TopUp(long id, long walletId, long amountPaise, long balancePaise, long toppedUpTodayPaise, long dailyLimitPaise, OffsetDateTime createdAt) {
    }

    private record Wallet(String tier, long dailyLimitPaise) {
    }

    private final JdbcClient jdbc;
    private final Clock clock;

    TopUps(JdbcClient jdbc, Clock clock) {
        this.jdbc = jdbc;
        this.clock = clock;
    }

    @Transactional
    TopUp topUp(long walletId, long amountPaise) {
        Instant now = clock.instant().truncatedTo(ChronoUnit.MICROS);   // what PostgreSQL keeps
        Wallet w = jdbc.sql("SELECT w.tier, t.daily_limit_paise FROM wallets w JOIN kyc_tiers t ON t.tier = w.tier WHERE w.id = ?")
                .param(walletId).query(Wallet.class).optional()
                .orElseThrow(() -> new ErrorResponseException(HttpStatus.NOT_FOUND, ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No such wallet"), null));
        // Lock exactly the rows we sum, not the whole wallet: other updates to the wallet are not blocked.
        LocalDate today = LocalDate.now(clock);
        long toppedUp = jdbc.sql("SELECT amount_paise FROM top_ups WHERE wallet_id = ? AND created_at >= ? AND created_at < ? FOR UPDATE")
                .params(walletId, at(today), at(today.plusDays(1))).query(Long.class).list().stream().mapToLong(Long::longValue).sum();
        if (toppedUp + amountPaise > w.dailyLimitPaise()) {
            long left = w.dailyLimitPaise() - toppedUp;
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, "The daily limit for " + w.tier() + "-KYC wallets is "
                    + rupees(w.dailyLimitPaise()) + "; " + rupees(toppedUp) + " was topped up today (IST), so at most " + rupees(left) + " more");
            p.setProperty("remainingTodayPaise", left);
            throw new ErrorResponseException(HttpStatus.CONFLICT, p, null);
        }
        long id = jdbc.sql("INSERT INTO top_ups (wallet_id, amount_paise, created_at) VALUES (?, ?, ?) RETURNING id")
                .params(walletId, amountPaise, at(now)).query(Long.class).single();
        long balance = jdbc.sql("UPDATE wallets SET balance_paise = balance_paise + ? WHERE id = ? RETURNING balance_paise")
                .params(amountPaise, walletId).query(Long.class).single();
        return new TopUp(id, walletId, amountPaise, balance, toppedUp + amountPaise, w.dailyLimitPaise(), at(now));
    }

    private static OffsetDateTime at(Instant i) {
        return i.atOffset(ZoneOffset.UTC);
    }

    private OffsetDateTime at(LocalDate day) {
        return at(day.atStartOfDay(clock.getZone()).toInstant());
    }

    /** ₹1,00,000.00: shown to people in India, so Indian digit grouping. */
    static String rupees(long paise) {
        // java.text.DecimalFormat keeps one grouping size, so the en-IN format prints 100,000.00: grouped here instead.
        String r = Long.toString(paise / 100);
        StringBuilder s = new StringBuilder(r.substring(Math.max(0, r.length() - 3)));
        for (int i = r.length() - 3; i > 0; i -= 2) {
            s.insert(0, r.substring(Math.max(0, i - 2), i) + ",");
        }
        return "₹" + s + "." + String.format(Locale.ROOT, "%02d", paise % 100);
    }
}
