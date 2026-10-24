package com.seatsure.sales;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static com.seatsure.sales.TestGateway.GATEWAY;
import static org.assertj.core.api.Assertions.assertThat;

/** The sale opens: sixteen fans at once, a gateway that takes 0.7 s per charge, a pool of four. Written first. */
@Import(PoolExhaustionTrapTest.OldWay.class)
class PoolExhaustionTrapTest extends ApiTest {

    /** The old way: one transaction around everything, so a connection is held while the gateway thinks. */
    @TestConfiguration
    static class OldWay {
        @Bean
        OldOrders oldOrders(TicketOrders orders, PaymentGateway gateway, JdbcClient jdbc) {
            return new OldOrders(orders, gateway, jdbc);
        }
    }

    static class OldOrders {
        private final TicketOrders orders;
        private final PaymentGateway gateway;
        private final JdbcClient jdbc;

        OldOrders(TicketOrders orders, PaymentGateway gateway, JdbcClient jdbc) {
            this.orders = orders;
            this.gateway = gateway;
            this.jdbc = jdbc;
        }

        @Transactional
        public String place(long saleId, String buyer, int seats) {
            TicketOrders.Order pending = orders.reserve(saleId, buyer, seats);
            PaymentGateway.Charge charge = gateway.charge(pending.id(), pending.amountPaise());
            jdbc.sql("UPDATE orders SET status = 'PAID', charge_id = ? WHERE id = ?").params(charge.chargeId(), pending.id()).update();
            return "PAID";
        }
    }

    @Autowired
    OldOrders oldOrders;

    List<String> sixteenFansAtOnce(Callable<String> buy) throws Exception {
        CountDownLatch open = new CountDownLatch(1);
        List<Future<String>> fans = new ArrayList<>();
        try (var threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 16; i++) {
                fans.add(threads.submit(() -> {
                    open.await();
                    try {
                        return buy.call();
                    } catch (Exception e) {
                        return e.getClass().getSimpleName();
                    }
                }));
            }
            open.countDown();
        }
        return fans.stream().map(Future::resultNow).toList();
    }

    @Test
    void theOldWayHoldsAConnectionThroughEachChargeAndFansTimeOut() throws Exception {
        GATEWAY.delayMillis = 700;
        double before = poolTimeouts();
        List<String> outcomes = sixteenFansAtOnce(() -> oldOrders.place(1, "fan", 1));
        // Four charges at a time, 0.7 s each: the fans still waiting after 1 s get no connection at all.
        assertThat(outcomes).contains("CannotGetJdbcConnectionException");
        assertThat(outcomes.stream().filter("PAID"::equals).count()).isLessThan(16);
        assertThat(poolTimeouts()).isGreaterThan(before);
    }

    @Test
    void theApiHoldsAConnectionForMillisecondsAndEveryFanGetsASeat() throws Exception {
        GATEWAY.delayMillis = 700;
        double before = poolTimeouts();
        List<String> outcomes = sixteenFansAtOnce(() -> String.valueOf(order(1, "fan", 1).andReturn().getResponse().getStatus()));
        assertThat(outcomes).containsOnly("201");
        assertThat(sold(1)).isEqualTo(16);
        assertThat(poolTimeouts()).isEqualTo(before);
    }
}
