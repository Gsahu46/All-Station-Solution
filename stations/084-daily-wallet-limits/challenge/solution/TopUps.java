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

    record Limits(String tier, long dailyLimitPaise, long toppedUpTodayPaise, long remainingTodayPaise, OffsetDateTime resetsAt) {
    }

    record Reversal(long topUpId, long walletId, long amountPaise, long balancePaise) {
    }

    private record Wallet(String tier, long dailyLimitPaise) {
    }

    private record Row(long amountPaise, boolean reversed) {
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
        // Lock the wallet row before summing: a second top-up for this wallet waits here until the first one commits,
        // and then sums again, seeing it. Locking today's top-up rows instead would lock nothing for the day's first one.
        Wallet w = wallet(walletId, " FOR UPDATE OF w");
        long toppedUp = toppedUpOn(walletId, LocalDate.ofInstant(now, IST));
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

    @Transactional(readOnly = true)
    Limits limits(long walletId) {
        Wallet w = wallet(walletId, "");
        LocalDate today = LocalDate.ofInstant(clock.instant(), IST);
        long toppedUp = toppedUpOn(walletId, today);
        return new Limits(w.tier(), w.dailyLimitPaise(), toppedUp, w.dailyLimitPaise() - toppedUp, at(today.plusDays(1)));
    }

    @Transactional
    Reversal reverse(long walletId, long topUpId) {
        wallet(walletId, " FOR UPDATE OF w");   // the balance and the day's total change together, as in topUp
        Row r = jdbc.sql("SELECT amount_paise, reversed_at IS NOT NULL AS reversed FROM top_ups WHERE id = ? AND wallet_id = ?")
                .params(topUpId, walletId).query(Row.class).optional()
                .orElseThrow(() -> new ErrorResponseException(HttpStatus.NOT_FOUND, ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No such top-up on this wallet"), null));
        long balance = jdbc.sql("SELECT balance_paise FROM wallets WHERE id = ?").param(walletId).query(Long.class).single();
        if (r.reversed()) {
            return new Reversal(topUpId, walletId, r.amountPaise(), balance);   // already reversed: the same answer
        }
        if (balance < r.amountPaise()) {
            throw new ErrorResponseException(HttpStatus.CONFLICT, ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT,
                    "The wallet holds " + rupees(balance) + ", less than the " + rupees(r.amountPaise()) + " top-up"), null);
        }
        jdbc.sql("UPDATE top_ups SET reversed_at = ? WHERE id = ?").params(at(clock.instant().truncatedTo(ChronoUnit.MICROS)), topUpId).update();
        balance = jdbc.sql("UPDATE wallets SET balance_paise = balance_paise - ? WHERE id = ? RETURNING balance_paise")
                .params(r.amountPaise(), walletId).query(Long.class).single();
        return new Reversal(topUpId, walletId, r.amountPaise(), balance);
    }

    private Wallet wallet(long walletId, String lock) {
        return jdbc.sql("SELECT w.tier, t.daily_limit_paise FROM wallets w JOIN kyc_tiers t ON t.tier = w.tier WHERE w.id = ?" + lock)
                .param(walletId).query(Wallet.class).optional()
                .orElseThrow(() -> new ErrorResponseException(HttpStatus.NOT_FOUND, ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No such wallet"), null));
    }

    private long toppedUpOn(long walletId, LocalDate istDay) {
        return jdbc.sql("SELECT coalesce(sum(amount_paise), 0) FROM top_ups WHERE wallet_id = ? AND reversed_at IS NULL AND created_at >= ? AND created_at < ?")
                .params(walletId, at(istDay), at(istDay.plusDays(1))).query(Long.class).single();
    }

    private static OffsetDateTime at(Instant i) {
        return i.atOffset(ZoneOffset.UTC);
    }

    private static OffsetDateTime at(LocalDate istDay) {
        return at(istDay.atStartOfDay(IST).toInstant());
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
