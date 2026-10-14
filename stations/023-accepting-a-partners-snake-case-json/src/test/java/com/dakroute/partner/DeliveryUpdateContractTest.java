package com.dakroute.partner;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: the partner's shape in, our shape out, times converted, and every refusal. */
class DeliveryUpdateContractTest extends ApiTest {

    static String payload(String awb, String status, String eventTime) {
        return "{\"awb_number\":\"" + awb + "\",\"status_code\":\"" + status + "\",\"event_time\":\"" + eventTime + "\"}";
    }

    @Test
    void snakeCaseInCamelCaseOutAndEveryTimeInUtc() throws Exception {
        update(PARTNER_PAYLOAD)
                .andExpect(jsonPath("$.accepted").value(true))
                .andExpect(jsonPath("$.event.at").value("2026-10-14T03:45:00Z"))           // 09:15 IST is 03:45 UTC
                .andExpect(jsonPath("$.event.promisedBy").value("2026-10-14T12:30:00Z"))   // +05:30 read as an exact instant
                .andExpect(jsonPath("$.event.city").value("Pune"))
                .andExpect(jsonPath("$.event.pinCode").value("411001"))
                .andExpect(jsonPath("$.event.partnerStatusCode").value("OFD"))
                .andExpect(jsonPath("$.event.awb_number").doesNotExist());
    }

    @Test
    void anIndianLateNightTimeIsTheDayBeforeInUtc() throws Exception {
        update(payload("dkr100000002in", "DLV", "2026-10-15 02:00:00"))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.event.awbNumber").value("DKR100000002IN"))
                .andExpect(jsonPath("$.event.status").value("DELIVERED"))
                .andExpect(jsonPath("$.event.at").value("2026-10-14T20:30:00Z"));
    }

    @Test
    void aStatusCodeWeDoNotKnowYetIsKeptAsUnknown() throws Exception {
        update(payload("DKR100000001IN", "HLD", "2026-10-14 10:00:00"))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.event.status").value("UNKNOWN"))
                .andExpect(jsonPath("$.event.partnerStatusCode").value("HLD"));
    }

    @Test
    void anAwbWeNeverBookedIs404() throws Exception {
        update(payload("DKR999999999IN", "OFD", "2026-10-14 09:15:00"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Unknown AWB"));
    }

    @Test
    void missingOrMalformedFieldsAre400() throws Exception {
        update("{\"status_code\":\"OFD\",\"event_time\":\"2026-10-14 09:15:00\"}").andExpect(status().isBadRequest());
        update(payload("DKR100000001IN", "OFD", "14/10/2026 09:15")).andExpect(status().isBadRequest());
        update(payload("DKR100000001IN", "OFD", "2026-10-14T09:15:00")).andExpect(status().isBadRequest());   // not the agreed format
        update(payload("DKR-1", "OFD", "2026-10-14 09:15:00")).andExpect(status().isBadRequest());
        update(payload("DKR100000001IN", "", "2026-10-14 09:15:00")).andExpect(status().isBadRequest());
        update(PARTNER_PAYLOAD.replace("\"411001\"", "\"4110\"")).andExpect(status().isBadRequest());
        // a client sending our camelCase names instead of theirs: awb_number is missing
        update("{\"awbNumber\":\"DKR100000001IN\",\"statusCode\":\"OFD\",\"eventTime\":\"2026-10-14 09:15:00\"}")
                .andExpect(status().isBadRequest());
    }
}
