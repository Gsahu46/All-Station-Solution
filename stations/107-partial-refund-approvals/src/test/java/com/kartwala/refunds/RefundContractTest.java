package com.kartwala.refunds;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class RefundContractTest extends ApiTest {

    @Test
    void upToFiveThousandRupeesIsApprovedAtOnceAboveItWaitsForASecondPerson() throws Exception {
        refund(WASHING_MACHINE, 500_000, "asha").andExpect(status().isCreated()).andExpect(header().string("Location", "/refunds/1"))
                .andExpect(jsonPath("$.status").value("APPROVED")).andExpect(jsonPath("$.needsSecondApproval").value(false))
                .andExpect(jsonPath("$.decidedBy").value("asha"));
        long big = idOf(refund(WASHING_MACHINE, 500_001, "asha").andExpect(status().isCreated())
                .andExpect(jsonPath("$.status").value("PENDING_APPROVAL")).andExpect(jsonPath("$.decidedBy").isEmpty()));

        decide(big, "APPROVE", "raj").andExpect(status().isOk()).andExpect(jsonPath("$.status").value("APPROVED"))
                .andExpect(jsonPath("$.decidedBy").value("raj"));
        mvc.perform(get("/orders/{id}", WASHING_MACHINE).with(httpBasic("raj", "raj-demo-pass"))).andExpect(status().isOk())
                .andExpect(jsonPath("$.totalPaise").value(1_250_000)).andExpect(jsonPath("$.reservedPaise").value(1_000_001))
                .andExpect(jsonPath("$.remainingPaise").value(249_999)).andExpect(jsonPath("$.refunds.length()").value(2));
    }

    @Test
    void theAskerCannotApproveARejectionGivesTheAmountBackAndADecisionIsFinal() throws Exception {
        long id = idOf(refund(PHONE, 1_000_000, "meena"));
        decide(id, "APPROVE", "meena").andExpect(status().isForbidden())
                .andExpect(jsonPath("$.detail").value("You asked for this refund; another approver must decide it."));
        decide(id, "REJECT", "raj").andExpect(status().isOk()).andExpect(jsonPath("$.status").value("REJECTED"));
        org.assertj.core.api.Assertions.assertThat(reserved(PHONE)).isZero();
        decide(id, "APPROVE", "raj").andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("This refund is already REJECTED."));
    }

    @Test
    void moreThanIsLeftIs409WithWhatIsLeft() throws Exception {
        refund(MIXER, 300_000, "asha").andExpect(status().isCreated());
        refund(MIXER, 200_000, "vikram").andExpect(status().isConflict())
                .andExpect(jsonPath("$.detail").value("Only ₹1,999.00 of this order can still be refunded."))
                .andExpect(jsonPath("$.remainingPaise").value(199_900));
    }

    @Test
    void badInputIs400UnknownThingsAre404AndRolesAreChecked() throws Exception {
        refund(MIXER, 0, "asha").andExpect(status().isBadRequest());
        mvc.perform(post("/orders/{id}/refunds", MIXER).with(httpBasic("asha", "asha-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"amountPaise\":1000,\"reason\":\" \"}")).andExpect(status().isBadRequest());
        mvc.perform(post("/orders/{id}/refunds", MIXER).with(httpBasic("asha", "asha-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"reason\":\"no amount\"}")).andExpect(status().isBadRequest());
        decide(1, "MAYBE", "raj").andExpect(status().isBadRequest());

        refund(9999, 1_000, "asha").andExpect(status().isNotFound());
        decide(9999, "APPROVE", "raj").andExpect(status().isNotFound());
        mvc.perform(get("/orders/{id}", 9999).with(httpBasic("raj", "raj-demo-pass"))).andExpect(status().isNotFound());

        mvc.perform(post("/refunds/{id}/approvals", 1).contentType(MediaType.APPLICATION_JSON).content("{\"decision\":\"APPROVE\"}"))
                .andExpect(status().isUnauthorized());
        decide(1, "APPROVE", "asha").andExpect(status().isForbidden());   // an agent, not an approver
        refund(MIXER, 1_000, "raj").andExpect(status().isForbidden());    // an approver, not an agent
    }
}
