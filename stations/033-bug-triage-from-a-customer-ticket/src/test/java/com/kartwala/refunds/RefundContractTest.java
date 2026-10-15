package com.kartwala.refunds;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract. KW-1041 has a ₹200 coupon (kurta L1, dupatta L2); KW-1042, the ticket's order, has none. */
class RefundContractTest extends ApiTest {

    @Test
    void theTicketsExactRequestIsRecorded() throws Exception {
        refund("""
                {"orderId":"KW-1042","lineIds":["L2"]}""")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.amountPaise").value(59_900))
                .andExpect(jsonPath("$.status").value("RECORDED"));
    }

    @Test
    void theWholeOrderPathWorksWithoutACouponToo() throws Exception {
        refund("""
                {"orderId":"kw-1042"}""")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.orderId").value("KW-1042"))
                .andExpect(jsonPath("$.lineIds", contains("L1", "L2")))
                .andExpect(jsonPath("$.amountPaise").value(259_800));
    }

    @Test
    void partRefundsOfACouponOrderAddUpToWhatWasPaid() throws Exception {
        refund("""
                {"orderId":"KW-1041","lineIds":["l2","L2"]}""")
                .andExpect(jsonPath("$.lineIds", contains("L2")))
                .andExpect(jsonPath("$.amountPaise").value(44_350));
        refund("""
                {"orderId":"KW-1041"}""")
                .andExpect(jsonPath("$.lineIds", contains("L1")))
                .andExpect(jsonPath("$.amountPaise").value(115_450));
    }

    @Test
    void aLineIsRefundedOnce() throws Exception {
        refund("""
                {"orderId":"KW-1042","lineIds":["L2"]}""").andExpect(status().isCreated());
        refund("""
                {"orderId":"KW-1042","lineIds":["L2"]}""").andExpect(status().isConflict())
                .andExpect(jsonPath("$.detail").value("Line L2 of KW-1042 is already refunded."));
        refund("""
                {"orderId":"KW-1042"}""").andExpect(jsonPath("$.lineIds", contains("L1")));
        refund("""
                {"orderId":"KW-1042"}""").andExpect(status().isConflict());
    }

    @Test
    void unknownOrdersAndLinesAreRefused() throws Exception {
        refund("""
                {"orderId":"KW-9999","lineIds":["L1"]}""").andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
        refund("""
                {"orderId":"KW-1042","lineIds":["L9"]}""").andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.title").value("Unknown line"));
    }

    @Test
    void badBodiesAre400() throws Exception {
        refund("""
                {"lineIds":["L1"]}""").andExpect(status().isBadRequest());
        refund("""
                {"orderId":"1042"}""").andExpect(status().isBadRequest());
        refund("""
                {"orderId":"KW-1042","lineIds":["belt"]}""").andExpect(status().isBadRequest());
        refund("""
                {"orderId":"KW-1042","amountPaise":1}""").andExpect(status().isBadRequest());
        refund("not json").andExpect(status().isBadRequest());
    }
}
