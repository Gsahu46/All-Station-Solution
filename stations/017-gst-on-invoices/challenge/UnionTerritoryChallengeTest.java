package com.billora.invoices;

import org.junit.jupiter.api.Test;
import org.springframework.test.context.TestPropertySource;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 2: a seller in Chandigarh (state code 04, a union territory). Inside the same union territory the
 * tax is CGST + UTGST instead of CGST + SGST; to any other state or territory it is IGST, as before.
 */
@TestPropertySource(properties = "billora.seller-state=CHANDIGARH")
class UnionTerritoryChallengeTest extends ApiTest {

    @Test
    void withinTheSameUnionTerritoryItIsCgstAndUtgst() throws Exception {
        preview("2026-10-13", "04", oneLine("8471", 100_000))
                .andExpect(jsonPath("$.sellerState").value("04-Chandigarh"))
                .andExpect(jsonPath("$.supplyType").value("INTRA_STATE"))
                .andExpect(jsonPath("$.cgstPaise").value(9_000))
                .andExpect(jsonPath("$.utgstPaise").value(9_000))
                .andExpect(jsonPath("$.sgstPaise").value(0))
                .andExpect(jsonPath("$.taxSummary[0].utgstPaise").value(9_000))
                .andExpect(jsonPath("$.totalTaxPaise").value(18_000));
    }

    @Test
    void toAStateItIsIgst() throws Exception {
        preview("2026-10-13", "29", oneLine("8471", 100_000))
                .andExpect(jsonPath("$.igstPaise").value(18_000))
                .andExpect(jsonPath("$.utgstPaise").value(0));
    }
}
