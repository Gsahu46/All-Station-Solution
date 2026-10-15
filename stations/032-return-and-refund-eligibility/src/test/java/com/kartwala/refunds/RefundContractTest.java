package com.kartwala.refunds;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * HTTP contract with the demo orders and a fixed clock: 15 October 2026, 11:30 in India. KW-1001 kurta delivered
 * 14 days before, KW-1002 innerwear 3, KW-1003 earbuds 9, KW-1004 phone 2, KW-1005 groceries 1; KW-1006 not delivered.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(RefundContractTest.FixedClock.class)
class RefundContractTest {

    @TestConfiguration
    static class FixedClock {
        @Bean
        @Primary
        Clock fixedClock() {
            return Clock.fixed(Instant.parse("2026-10-15T06:00:00Z"), ZoneOffset.UTC);
        }
    }

    @Autowired
    MockMvc mvc;

    ResultActions check(String json) throws Exception {
        return mvc.perform(post("/refund-eligibility-checks").contentType(MediaType.APPLICATION_JSON).content(json));
    }

    @Test
    void aKurtaTwoWeeksLaterIsEligibleWithThePickupFee() throws Exception {
        check("""
                {"orderId":"kw-1001","reason":"SIZE_ISSUE","tagsAttached":true}""")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.orderId").value("KW-1001"))
                .andExpect(jsonPath("$.eligible").value(true))
                .andExpect(jsonPath("$.reasons", empty()))
                .andExpect(jsonPath("$.refundPaise").value(125_000))
                .andExpect(jsonPath("$.lastDayToReturn").value("2026-10-31"));
    }

    @Test
    void refusalsListEveryReason() throws Exception {
        check("""
                {"orderId":"KW-1003","reason":"CHANGED_MIND","sealIntact":false}""")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.eligible").value(false))
                .andExpect(jsonPath("$.reasons", contains("WINDOW_CLOSED", "REASON_NOT_ACCEPTED", "SEAL_BROKEN")))
                .andExpect(jsonPath("$.refundPaise").value(0));
        check("""
                {"orderId":"KW-1006","reason":"CHANGED_MIND"}""")
                .andExpect(jsonPath("$.reasons", contains("NOT_DELIVERED")))
                .andExpect(jsonPath("$.lastDayToReturn").doesNotExist());
    }

    @Test
    void anUnknownOrderIs404() throws Exception {
        check("""
                {"orderId":"KW-9999","reason":"DAMAGED"}""")
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Order not found"));
    }

    @Test
    void badRequestsAre400() throws Exception {
        check("""
                {"orderId":"KW-1001","reason":"TOO_EXPENSIVE","tagsAttached":true}""").andExpect(status().isBadRequest());
        check("""
                {"orderId":"KW-1001","tagsAttached":true}""").andExpect(status().isBadRequest());
        check("""
                {"orderId":"order 1","reason":"DAMAGED"}""").andExpect(status().isBadRequest());
        check("""
                {"orderId":"KW-1001","reason":"DAMAGED","tagsAttached":true,"refundPaise":999999}""").andExpect(status().isBadRequest());
        check("""
                {"orderId":"KW-1001","reason":"SIZE_ISSUE"}""").andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("tagsAttached is required for clothing."));
    }
}
