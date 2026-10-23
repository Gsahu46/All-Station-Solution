package com.dakroute.shipments;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 2: a seller whose upload timed out sends the same file again. An item identical to a shipment already
 * created under its ref is "existing" with that shipment's id, not a failure; the same ref with different details
 * still fails, as before. The report counts them under "existing".
 */
class ResubmitChallengeTest extends ApiTest {

    @Test
    void theSameFileTwiceCreatesEachShipmentOnce() throws Exception {
        bulk(List.of(item("ORD-1"), item("ORD-2")));
        bulk(List.of(item("ORD-1"), item("ORD-2"), item("ORD-3"))).andExpect(jsonPath("$.created").value(1))
                .andExpect(jsonPath("$.existing").value(2)).andExpect(jsonPath("$.failed").value(0))
                .andExpect(jsonPath("$.results[0].status").value("existing")).andExpect(jsonPath("$.results[0].shipmentId").value(1))
                .andExpect(jsonPath("$.results[2].status").value("created"));
        assertThat(count()).isEqualTo(3);
    }

    @Test
    void theSameRefWithOtherDetailsStillFails() throws Exception {
        bulk(List.of(item("ORD-1")));
        bulk(List.of(item("ORD-1").replace("1200", "1500"))).andExpect(jsonPath("$.failed").value(1))
                .andExpect(jsonPath("$.results[0].errors[0].message").value("is already used by another shipment"));
    }
}
