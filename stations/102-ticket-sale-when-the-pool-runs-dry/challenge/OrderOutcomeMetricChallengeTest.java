package com.seatsure.sales;

import org.junit.jupiter.api.Test;

import static com.seatsure.sales.TestGateway.GATEWAY;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: the pool's metrics say the database is fine or not; this one says how orders end. A counter
 * ticket.orders tagged outcome = paid, declined, gateway_timeout, gateway_error or no_seats, published at /actuator/metrics.
 */
class OrderOutcomeMetricChallengeTest extends ApiTest {

    double outcome(String name) {
        var c = metrics.find("ticket.orders").tag("outcome", name).counter();
        return c == null ? 0 : c.count();
    }

    @Test
    void everyOrderIsCountedByHowItEnded() throws Exception {
        double paid = outcome("paid"), declined = outcome("declined"), noSeats = outcome("no_seats");
        order(2, "Priya Nair", 4).andExpect(status().isCreated());
        order(2, "Ravi Kumar", 1).andExpect(status().isConflict());
        GATEWAY.status = 402;
        order(1, "Ravi Kumar", 1).andExpect(status().isPaymentRequired());
        assertThat(outcome("paid")).isEqualTo(paid + 1);
        assertThat(outcome("no_seats")).isEqualTo(noSeats + 1);
        assertThat(outcome("declined")).isEqualTo(declined + 1);
        mvc.perform(get("/actuator/metrics/ticket.orders")).andExpect(status().isOk()).andExpect(jsonPath("$.name").value("ticket.orders"));
    }

    @Test
    void aHangingGatewayIsCountedAsATimeout() throws Exception {
        double before = outcome("gateway_timeout");
        GATEWAY.delayMillis = 2_000;
        order(1, "Priya Nair", 1).andExpect(status().isGatewayTimeout());
        assertThat(outcome("gateway_timeout")).isEqualTo(before + 1);
    }
}
