package com.basketo.referrals;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;

/**
 * Referrals are recorded at sign-up and rewarded only when the new customer's first qualifying order is delivered.
 * Each rule that matters is also a constraint: one referral per new customer and per device, one reward per referral
 * and per order.
 */
@Service
class Referrals {

    enum Outcome { REWARDED, ALREADY_REWARDED, NOT_REFERRED, BELOW_MINIMUM }

    record SignUp(long customerId, String referralCode, long referralId, String status) {
    }

    record Result(Outcome outcome, Long rewardId, Long referrerId, long amountPaise) {
    }

    record Reward(long id, long referralId, long orderId, long referrerId, long amountPaise, String delivery, int attempts, String lastError) {
    }

    static final class NoSuchCode extends RuntimeException {
    }

    static final class PhoneTaken extends RuntimeException {
    }

    /** The code belongs to this phone, or this device already has an account or a referral. */
    static final class NotANewCustomer extends RuntimeException {
        NotANewCustomer(String message) {
            super(message);
        }
    }

    private static final String CODE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    private static final SecureRandom RANDOM = new SecureRandom();
    private final JdbcClient jdbc;
    private final long rewardPaise;
    private final long minimumOrderPaise;
    private final RestClient wallet;

    Referrals(JdbcClient jdbc, @Value("${basketo.referrals.reward-paise}") long rewardPaise,
              @Value("${basketo.referrals.minimum-order-paise}") long minimumOrderPaise, @Value("${basketo.wallet.url}") String walletUrl) {
        this.jdbc = jdbc;
        this.wallet = RestClient.create(walletUrl);
        this.rewardPaise = rewardPaise;
        this.minimumOrderPaise = minimumOrderPaise;
    }

    /** A new customer signs up with someone's code: the customer and a PENDING referral. No reward yet. */
    @Transactional
    SignUp signUp(String code, String name, String phone, String deviceId) {
        record Referrer(long id, String phone, String deviceId) {
        }
        Referrer referrer = jdbc.sql("SELECT id, phone, device_id FROM customers WHERE referral_code = ?").param(code.strip().toUpperCase(Locale.ROOT))
                .query(Referrer.class).optional().orElseThrow(NoSuchCode::new);
        if (referrer.phone().equals(phone) || referrer.deviceId().equals(deviceId)) {
            throw new NotANewCustomer("This referral code belongs to you; codes are for inviting someone new.");
        }
        if (jdbc.sql("SELECT count(*) FROM customers WHERE device_id = ?").param(deviceId).query(Integer.class).single() > 0) {
            throw new NotANewCustomer("This device already has a Basketo account; referral codes are for new customers.");
        }
        long customer;
        try {
            customer = jdbc.sql("INSERT INTO customers (name, phone, device_id, referral_code) VALUES (?, ?, ?, ?) RETURNING id")
                    .params(name, phone, deviceId, newCode()).query(Long.class).single();
        } catch (DuplicateKeyException e) {
            throw new PhoneTaken();
        }
        long referral;
        try {
            referral = jdbc.sql("INSERT INTO referrals (referrer_id, referee_id, device_id, status) VALUES (?, ?, ?, 'PENDING') RETURNING id")
                    .params(referrer.id(), customer, deviceId).query(Long.class).single();
        } catch (DuplicateKeyException e) {
            // Two sign-ups on one device at the same moment: the check above passed for both; the constraint did not.
            throw new NotANewCustomer("This device already has a Basketo account; referral codes are for new customers.");
        }
        String newCode = jdbc.sql("SELECT referral_code FROM customers WHERE id = ?").param(customer).query(String.class).single();
        return new SignUp(customer, newCode, referral, "PENDING");
    }

    /**
     * The order service reports a delivered order. Delivered at least once: the same event may come twice, and the
     * answer is the same reward. The unique constraints stop a second reward, so no lock is needed.
     */
    @Transactional
    Result orderDelivered(long orderId, long customerId, long totalPaise) {
        record Referral(long id, long referrerId, String status) {
        }
        Optional<Referral> referral = jdbc.sql("SELECT id, referrer_id, status FROM referrals WHERE referee_id = ?").param(customerId)
                .query(Referral.class).optional();
        if (referral.isEmpty()) {
            return new Result(Outcome.NOT_REFERRED, null, null, 0);
        }
        if (referral.get().status().equals("REWARDED")) {
            return jdbc.sql("SELECT id, referrer_id, amount_paise FROM rewards WHERE referral_id = ?").param(referral.get().id())
                    .query((rs, n) -> new Result(Outcome.ALREADY_REWARDED, rs.getLong(1), rs.getLong(2), rs.getLong(3))).single();
        }
        if (totalPaise < minimumOrderPaise) {
            return new Result(Outcome.BELOW_MINIMUM, null, null, 0);
        }
        long reward = jdbc.sql("INSERT INTO rewards (referral_id, order_id, referrer_id, amount_paise) VALUES (?, ?, ?, ?) RETURNING id")
                .params(referral.get().id(), orderId, referral.get().referrerId(), rewardPaise).query(Long.class).single();
        jdbc.sql("UPDATE referrals SET status = 'REWARDED' WHERE id = ?").param(referral.get().id()).update();
        // Credit the wallet right away: no outbox table and no scheduler to run.
        wallet.post().uri("/credits").header("Idempotency-Key", "referral-reward-" + reward)
                .body(Map.of("customerId", referral.get().referrerId(), "amountPaise", rewardPaise, "reason", "referral reward"))
                .retrieve().toBodilessEntity();
        return new Result(Outcome.REWARDED, reward, referral.get().referrerId(), rewardPaise);
    }

    Optional<Reward> reward(long id) {
        return jdbc.sql("""
                        SELECT r.id, r.referral_id, r.order_id, r.referrer_id, r.amount_paise, o.status AS delivery, o.attempts, o.last_error
                        FROM rewards r JOIN wallet_outbox o ON o.reward_id = r.id WHERE r.id = ?""").param(id).query(Reward.class).optional();
    }

    private static String newCode() {
        StringBuilder s = new StringBuilder("BK");
        for (int i = 0; i < 6; i++) {
            s.append(CODE_LETTERS.charAt(RANDOM.nextInt(CODE_LETTERS.length())));
        }
        return s.toString();
    }
}
