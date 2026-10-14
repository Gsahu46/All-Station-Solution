package com.tiffino.orders;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The first test written for this station: it reproduces the bugs before the fix. */
class AnyStatusTrapTest extends ApiTest {

    /** The "before" order: a status field the client sets to whatever it sends. Kept only in tests. */
    static final class OldOrder {
        String status = "PLACED";

        void setStatus(String to) {
            status = to;
        }
    }

    @Test
    void theOldOrderAcceptsDeliveredBeforeItWasEvenAccepted() {
        OldOrder order = new OldOrder();
        order.setStatus("DELIVERED");
        assertThat(order.status).isEqualTo("DELIVERED");   // the customer is told their food arrived
    }

    @Test
    void theOldOrderLetsACancelledOrderBePickedUp() {
        OldOrder order = new OldOrder();
        order.setStatus("CANCELLED");
        order.setStatus("PICKED_UP");
        assertThat(order.status).isEqualTo("PICKED_UP");   // a rider collects food nobody will pay for
    }

    @Test
    void theRealFlowRefusesBothWith409() throws Exception {
        change(1001, "DELIVERED").andExpect(status().isConflict())
                .andExpect(jsonPath("$.detail").value("Order 1001 cannot go from PLACED to DELIVERED. Allowed next: [ACCEPTED, REJECTED, CANCELLED]."));
        change(1002, "PICKED_UP").andExpect(status().isConflict())
                .andExpect(jsonPath("$.detail").value("Order 1002 cannot go from CANCELLED to PICKED_UP. It is CANCELLED: nothing can change now."));
    }
}
