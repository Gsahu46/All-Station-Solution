package com.billora.invoices;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: an optional discountPaise per line. Tax is on the value after the discount, and (in this station's
 * rules) the price slab uses the price per piece after the discount. Each line shows its discount.
 */
class DiscountChallengeTest extends ApiTest {

    static String jacket(int quantity, long discountPaise) {
        return "[{\"description\":\"Jersey\",\"hsn\":\"6109\",\"quantity\":" + quantity
                + ",\"unitPricePaise\":260000,\"discountPaise\":" + discountPaise + "}]";
    }

    @Test
    void aDiscountLowersTheTaxableValueAndCanMoveTheSlab() throws Exception {
        preview("2026-10-13", "29", jacket(2, 40_000))            // Rs 2,600 each, Rs 400 off the line: Rs 2,400 a piece
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.lines[0].discountPaise").value(40_000))
                .andExpect(jsonPath("$.lines[0].taxableValuePaise").value(480_000))
                .andExpect(jsonPath("$.lines[0].ratePercent").value(5))   // not 18: below the Rs 2,500 slab after the discount
                .andExpect(jsonPath("$.totalTaxPaise").value(24_000));
    }

    @Test
    void withoutADiscountNothingChanges() throws Exception {
        preview("2026-10-13", "29", oneLine("6109", 260_000))
                .andExpect(jsonPath("$.lines[0].discountPaise").value(0))
                .andExpect(jsonPath("$.lines[0].ratePercent").value(18));
    }

    @Test
    void aDiscountOfTheWholeLineOrMoreIsRefused() throws Exception {
        preview("2026-10-13", "29", jacket(1, 260_000)).andExpect(status().isUnprocessableContent());
        preview("2026-10-13", "29", jacket(1, -1)).andExpect(status().isBadRequest());
    }
}
