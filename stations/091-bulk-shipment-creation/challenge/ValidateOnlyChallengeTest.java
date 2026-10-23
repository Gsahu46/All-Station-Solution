package com.dakroute.shipments;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: POST /shipments/bulk?validateOnly=true checks a batch without saving it, so a seller can fix a file
 * before sending it for real. Good items are "valid"; bad ones "failed" with the same errors as a real call,
 * including a ref already used.
 */
class ValidateOnlyChallengeTest extends ApiTest {

    @Test
    void aDryRunReportsAndSavesNothing() throws Exception {
        bulk(java.util.List.of(item("ORD-1")));
        String body = "{\"shipments\":[" + item("ORD-1").replace("1200", "1500") + "," + item("ORD-2") + "," + item("ORD-3").replace("110003", "11003") + "]}";
        mvc.perform(post("/shipments/bulk").param("validateOnly", "true").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk()).andExpect(jsonPath("$.created").value(0)).andExpect(jsonPath("$.failed").value(2))
                .andExpect(jsonPath("$.results[0].errors[0].message").value("is already used by another shipment"))
                .andExpect(jsonPath("$.results[1].status").value("valid"))
                .andExpect(jsonPath("$.results[2].errors[0].field").value("to.pincode"));
        assertThat(count()).isOne();
    }
}
