package com.basketo.referrals;

import org.junit.jupiter.api.Test;

import static com.basketo.referrals.TestWallet.WALLET;
import static org.assertj.core.api.Assertions.assertThat;

/** The wallet credit travels through the outbox: retried while it may pass, parked when it cannot, never paid twice. */
class WalletMessagingTest extends ApiTest {

    long rewardFor(String phone, String device, long order) throws Exception {
        long customer = referredCustomer(phone, device);
        return json(order(order, customer, 70_000, "DELIVERED")).path("rewardId").asLong();
    }

    String lastError(long reward) {
        return jdbc.sql("SELECT last_error FROM wallet_outbox WHERE reward_id = ?").param(reward).query(String.class).single();
    }

    int attempts(long reward) {
        return jdbc.sql("SELECT attempts FROM wallet_outbox WHERE reward_id = ?").param(reward).query(Integer.class).single();
    }

    @Test
    void aBusyWalletIsTriedAgainWithTheSameKeyUntilItAnswers() throws Exception {
        WALLET.planned.add(503);
        WALLET.planned.add(503);
        long reward = rewardFor("9876500030", "device-new-0030", 7201);
        awaitDelivery(reward, "SENT");
        assertThat(attempts(reward)).isEqualTo(3);
        assertThat(WALLET.requests).hasSize(3).allMatch(r -> r.key().equals("referral-reward-" + reward));
        assertThat(WALLET.creditedTo(PRIYA)).isEqualTo(10_000);
    }

    @Test
    void aWalletThatNeverAnswersWellParksTheCreditAsDead() throws Exception {
        for (int i = 0; i < 10; i++) {
            WALLET.planned.add(503);
        }
        long reward = rewardFor("9876500031", "device-new-0031", 7202);
        awaitDelivery(reward, "DEAD");
        assertThat(attempts(reward)).isEqualTo(3);
        assertThat(lastError(reward)).startsWith("gave up after 3 tries");
        Thread.sleep(500);   // five more polls
        assertThat(WALLET.requests).as("nothing sent after it is parked").hasSize(3);
        assertThat(WALLET.creditedTo(PRIYA)).isZero();
    }

    @Test
    void aRefusedCreditIsDeadAtOnce() throws Exception {
        WALLET.planned.add(400);
        long reward = rewardFor("9876500032", "device-new-0032", 7203);
        awaitDelivery(reward, "DEAD");
        assertThat(attempts(reward)).isEqualTo(1);
        assertThat(lastError(reward)).isEqualTo("the wallet refused the credit: 400");
    }

    @Test
    void aCreditAppliedButAnsweredTooLateIsSentAgainAndPaidOnce() throws Exception {
        WALLET.slowAfterApplyMillis = 1_500;   // the app waits 500 ms
        long reward = rewardFor("9876500033", "device-new-0033", 7204);
        awaitDelivery(reward, "SENT");
        assertThat(WALLET.requests).hasSizeGreaterThanOrEqualTo(2).allMatch(r -> r.key().equals("referral-reward-" + reward));
        assertThat(WALLET.creditedTo(PRIYA)).as("the key made the second request harmless").isEqualTo(10_000);
    }
}
