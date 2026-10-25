package com.basketo.referrals;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class ReferralContractTest extends ApiTest {

    @Test
    void aNewCustomerSignsUpWithACodeAndNothingIsPaidYet() throws Exception {
        var created = signUp("riya100", "098765 43210", "device-new-0001").andExpect(status().isCreated())
                .andExpect(jsonPath("$.status").value("PENDING")).andExpect(jsonPath("$.referralCode").value(org.hamcrest.Matchers.matchesPattern("BK[A-Z2-9]{6}")));
        long id = json(created).path("customerId").asLong();
        created.andExpect(header().string("Location", "/customers/" + id));
        assertThat(jdbc.sql("SELECT phone FROM customers WHERE id = ?").param(id).query(String.class).single()).isEqualTo("+919876543210");
        assertThat(count("rewards")).isZero();
    }

    @Test
    void codesPhonesAndDevicesThatAreNotNewAreRefused() throws Exception {
        signUp("NOSUCH1", "9876543210", "device-new-0002").andExpect(status().isNotFound());
        signUp("RIYA100", "+91 98989-89898", "device-new-0003").andExpect(status().isConflict())   // Karan's number, written differently
                .andExpect(jsonPath("$.detail").value("This phone number already has a Basketo account."));
        signUp("RIYA100", "9812345670", "device-new-0004").andExpect(status().isUnprocessableContent())   // Priya's own number
                .andExpect(jsonPath("$.detail").value("This referral code belongs to you; codes are for inviting someone new."));
        signUp("RIYA100", "9876500000", "device-karan-01").andExpect(status().isUnprocessableContent())   // Karan's phone, a new SIM
                .andExpect(jsonPath("$.detail").value("This device already has a Basketo account; referral codes are for new customers."));
        signUp("RIYA100", "12345", "device-new-0005").andExpect(status().isBadRequest());
        signUp("RIYA100", "9876500001", "bad device!").andExpect(status().isBadRequest());
        assertThat(count("customers")).isEqualTo(2);
    }

    @Test
    void onlyADeliveredFirstOrderOfAtLeastFiveHundredRupeesIsRewarded() throws Exception {
        long customer = referredCustomer("9876500010", "device-new-0010");
        order(7001, customer, 80_000, "PLACED").andExpect(status().isUnprocessableContent());
        order(7001, customer, 49_999, "DELIVERED").andExpect(status().isOk()).andExpect(jsonPath("$.outcome").value("BELOW_MINIMUM"));
        order(7002, KARAN, 90_000, "DELIVERED").andExpect(status().isOk()).andExpect(jsonPath("$.outcome").value("NOT_REFERRED"));
        long reward = json(order(7003, customer, 50_000, "DELIVERED").andExpect(status().isCreated())
                .andExpect(jsonPath("$.outcome").value("REWARDED")).andExpect(jsonPath("$.referrerId").value(PRIYA))
                .andExpect(jsonPath("$.amountPaise").value(10_000))).path("rewardId").asLong();

        awaitDelivery(reward, "SENT");
        mvc.perform(get("/rewards/{id}", reward).with(httpBasic("support", "support-demo-pass"))).andExpect(status().isOk())
                .andExpect(jsonPath("$.orderId").value(7003)).andExpect(jsonPath("$.delivery").value("SENT")).andExpect(jsonPath("$.attempts").value(1));
    }

    @Test
    void badEventsAre400UnknownRewards404AndEachServiceHasItsOwnDoor() throws Exception {
        mvc.perform(post("/orders/{id}/referral-reward", 1).with(httpBasic("orders", "orders-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"customerId\":1,\"totalPaise\":1000,\"status\":\"LOST\"}")).andExpect(status().isBadRequest());
        mvc.perform(post("/orders/{id}/referral-reward", 1).with(httpBasic("orders", "orders-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"totalPaise\":1000,\"status\":\"DELIVERED\"}")).andExpect(status().isBadRequest());
        mvc.perform(get("/rewards/{id}", 999).with(httpBasic("support", "support-demo-pass"))).andExpect(status().isNotFound());

        mvc.perform(post("/referrals").contentType(MediaType.APPLICATION_JSON).content("{}")).andExpect(status().isUnauthorized());
        mvc.perform(post("/orders/{id}/referral-reward", 1).with(httpBasic("signup", "signup-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"customerId\":1,\"totalPaise\":90000,\"status\":\"DELIVERED\"}")).andExpect(status().isForbidden());
    }
}
