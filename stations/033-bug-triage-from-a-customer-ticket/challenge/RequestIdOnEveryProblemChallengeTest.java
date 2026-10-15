package com.kartwala.refunds;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: support asks for the request id on every refusal, not just on 500s, so a customer who sees "already
 * refunded" can be traced too. Every problem response (400, 404, 409, 422) carries "requestId", equal to the
 * X-Request-Id header.
 */
class RequestIdOnEveryProblemChallengeTest extends ApiTest {

    @Test
    void refusalsCarryTheRequestId() throws Exception {
        refund("""
                {"orderId":"KW-9999"}""", "support-case-77").andExpect(status().isNotFound())
                .andExpect(jsonPath("$.requestId").value("support-case-77"));
        refund("""
                {"orderId":"KW-1042","lineIds":["L9"]}""", "support-case-78").andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.requestId").value("support-case-78"));
    }

    @Test
    void badBodiesCarryItToo() throws Exception {
        refund("not json", "support-case-79").andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.requestId").value("support-case-79"));
        refund("""
                {"orderId":"1042"}""", "support-case-80").andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.requestId").value("support-case-80"));
    }
}
