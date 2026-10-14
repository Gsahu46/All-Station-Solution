package com.billora.invoices;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: same-state and other-state invoices, rates on their dates, and every refusal. */
class TaxPreviewContractTest extends ApiTest {

    @Test
    void aSameStateInvoiceHasCgstAndSgstPerRate() throws Exception {
        preview("2026-10-13", "29", OFFICE_LINES)
                .andExpect(jsonPath("$.sellerState").value("29-Karnataka"))
                .andExpect(jsonPath("$.placeOfSupply").value("29-Karnataka"))
                .andExpect(jsonPath("$.taxSummary", hasSize(2)))
                .andExpect(jsonPath("$.taxSummary[0].ratePercent").value(5))
                .andExpect(jsonPath("$.taxSummary[0].taxableValuePaise").value(239_700))
                .andExpect(jsonPath("$.taxSummary[0].cgstPaise").value(5_993))
                .andExpect(jsonPath("$.taxSummary[1].taxableValuePaise").value(239_750))
                .andExpect(jsonPath("$.taxSummary[1].sgstPaise").value(21_578))
                .andExpect(jsonPath("$.taxableValuePaise").value(479_450))
                .andExpect(jsonPath("$.invoiceTotalPaise").value(479_450 + 55_142));
    }

    @Test
    void anotherStateGetsIgstOnly() throws Exception {
        preview("2026-10-13", "27", OFFICE_LINES)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.supplyType").value("INTER_STATE"))
                .andExpect(jsonPath("$.placeOfSupply").value("27-Maharashtra"))
                .andExpect(jsonPath("$.cgstPaise").value(0))
                .andExpect(jsonPath("$.sgstPaise").value(0))
                .andExpect(jsonPath("$.taxSummary[0].igstPaise").value(11_985))
                .andExpect(jsonPath("$.taxSummary[1].igstPaise").value(43_155))
                .andExpect(jsonPath("$.igstPaise").value(55_140));
    }

    @Test
    void theRateIsTheOneValidOnTheInvoiceDate() throws Exception {
        preview("2025-09-21", "29", oneLine("8415", 3_800_000)).andExpect(jsonPath("$.lines[0].ratePercent").value(28));
        preview("2025-09-22", "29", oneLine("8415", 3_800_000)).andExpect(jsonPath("$.lines[0].ratePercent").value(18));
    }

    @Test
    void anUnknownHsnOrADateBeforeGstIs422NamingTheLine() throws Exception {
        preview("2026-10-13", "29", "[" + oneLine("8471", 100).replaceAll("[\\[\\]]", "") + ","
                + oneLine("1234", 100).replaceAll("[\\[\\]]", "") + "]")
                .andExpect(status().isUnprocessableContent())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.detail").value("Line 2: no GST rate for HSN 1234 on 2026-10-13."));
        preview("2017-06-30", "29", oneLine("8471", 100)).andExpect(status().isUnprocessableContent());
    }

    @Test
    void badFieldsAre400() throws Exception {
        preview("2026-10-13", "99", oneLine("8471", 100)).andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title").value("Unknown state code"));
        preview("2026-10-13", "KA", oneLine("8471", 100)).andExpect(status().isBadRequest());
        preview("2026-10-13", "29", "[]").andExpect(status().isBadRequest());
        preview("2026-10-13", "29", oneLine("847", 100)).andExpect(status().isBadRequest());
        preview("2026-10-13", "29", oneLine("8471", 0)).andExpect(status().isBadRequest());
        preview("2026-10-13", "29", oneLine("8471", 100).replace("\"quantity\":1", "\"quantity\":1.5")).andExpect(status().isBadRequest());
        preview("13-10-2026", "29", oneLine("8471", 100)).andExpect(status().isBadRequest());
        mvc.perform(post("/invoices/tax-preview").contentType(MediaType.APPLICATION_JSON).content("{}")).andExpect(status().isBadRequest());
    }
}
