package com.dakroute.tracking;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: a shipment, the request id on every response, and every refusal. */
class ShipmentContractTest extends ApiTest {

    static final String UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

    @Test
    void aShipmentComesBackWithTheCallersRequestId() throws Exception {
        track("dkr100000001in", "app-7f3a9c21")
                .andExpect(status().isOk())
                .andExpect(header().string("X-Request-Id", "app-7f3a9c21"))
                .andExpect(jsonPath("$.awb").value("DKR100000001IN"))
                .andExpect(jsonPath("$.status").value("OUT_FOR_DELIVERY"))
                .andExpect(jsonPath("$.events", hasSize(2)))
                .andExpect(jsonPath("$.events[1].place").value("Pune"));
    }

    @Test
    void withoutAnIdTheServerMakesOne() throws Exception {
        track("DKR100000002IN").andExpect(header().string("X-Request-Id", matchesPattern(UUID)));
    }

    @Test
    void anUnknownShipmentIs404AndTheBodyNamesTheRequestId() throws Exception {
        track("DKR999999999IN", "support-case-41")
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Shipment not found"))
                .andExpect(jsonPath("$.requestId").value("support-case-41"));
    }

    @Test
    void aBadAwbIs400WithItsRequestId() throws Exception {
        track("DKR-1", "bad-awb-request-1").andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.requestId").value("bad-awb-request-1"));
    }

    @Test
    void evenAPathNoControllerHandlesGetsAnId() throws Exception {
        mvc.perform(get("/shipment/DKR100000001IN").header("X-Request-Id", "typo-path-0001"))
                .andExpect(status().isNotFound())
                .andExpect(header().string("X-Request-Id", "typo-path-0001"));   // an interceptor would never see this
    }

    @Test
    void anUnsafeIdIsReplacedNotEchoed() throws Exception {
        for (String unsafe : new String[]{"short", "has spaces in it", "a".repeat(65), "evil\tERROR forged-line"}) {
            track("DKR100000001IN", unsafe).andExpect(header().string("X-Request-Id", matchesPattern(UUID)));
        }
    }
}
