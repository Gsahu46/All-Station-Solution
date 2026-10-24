package com.seatsure.sales;

import org.junit.jupiter.api.Test;

import static com.seatsure.sales.TestGateway.GATEWAY;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class TicketOrderContractTest extends ApiTest {

    @Test
    void aPaidOrderTakesItsSeats() throws Exception {
        order(1, "Priya Nair", 2).andExpect(status().isCreated()).andExpect(header().string("Location", "/orders/1"))
                .andExpect(jsonPath("$.status").value("PAID")).andExpect(jsonPath("$.amountPaise").value(300000))
                .andExpect(jsonPath("$.chargeId").value("ch_1")).andExpect(jsonPath("$.seats").value(2));
        mvc.perform(get("/sales/1")).andExpect(jsonPath("$.sold").value(2)).andExpect(jsonPath("$.left").value(29998));
        assertThat(GATEWAY.idempotencyKeys).containsExactly("order-1");
    }

    @Test
    void aDeclinedPaymentGivesTheSeatsBack() throws Exception {
        GATEWAY.status = 402;
        order(1, "Priya Nair", 2).andExpect(status().isPaymentRequired()).andExpect(jsonPath("$.detail").value("The payment was declined."));
        assertThat(sold(1)).isZero();
        assertThat(jdbc.sql("SELECT status FROM orders WHERE id = 1").query(String.class).single()).isEqualTo("FAILED");
    }

    @Test
    void badOrdersAre400UnknownSales404AndASoldOutSale409() throws Exception {
        order(1, "Priya Nair", 0).andExpect(status().isBadRequest());
        order(1, "Priya Nair", 7).andExpect(status().isBadRequest());
        order(1, " ", 2).andExpect(status().isBadRequest());
        order(9, "Priya Nair", 2).andExpect(status().isNotFound());
        mvc.perform(get("/sales/9")).andExpect(status().isNotFound());
        order(2, "Priya Nair", 4).andExpect(status().isCreated());   // the small match has 4 seats
        order(2, "Ravi Kumar", 1).andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("Not enough seats left."));
        assertThat(GATEWAY.idempotencyKeys).hasSize(1);   // nothing charged for refused orders
    }
}
