package com.billora.invoicing;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: each line may carry "taxPercent" (a whole number from 0 to 40; absent means 0). A line's taxPaise is
 * amountPaise × taxPercent / 100, rounded half up to the paisa; the invoice shows taxPaise (the sum) and totalPaise
 * (amounts plus tax). The table stores the rate, with a named check. Rates are a demo rule, not tax advice.
 */
class LineTaxChallengeTest extends ApiTest {

    @Test
    void taxIsComputedPerLineAndRounded() throws Exception {
        create("""
                {"customerName":"Kaveri Textiles Pvt Ltd","lines":[
                  {"description":"Cloud hosting, March 2026","quantity":1,"unitPricePaise":499900,"taxPercent":18},
                  {"description":"Printed manual","quantity":1,"unitPricePaise":999,"taxPercent":5},
                  {"description":"Training voucher","quantity":1,"unitPricePaise":50000}]}""")
                .andExpect(status().isCreated())
                .andExpect(content().json("""
                        {"lines":[{"taxPercent":18,"taxPaise":89982},{"taxPercent":5,"taxPaise":50},{"taxPercent":0,"taxPaise":0}],
                         "taxPaise":90032,"totalPaise":640931}"""));
    }

    @Test
    void ratesOutsideTheRangeAreRefused() throws Exception {
        create(INVOICE.replace("\"quantity\":6,", "\"quantity\":6,\"taxPercent\":41,")).andExpect(status().isBadRequest());
        create(INVOICE).andExpect(status().isCreated());
        assertThatThrownBy(() -> jdbc.sql("UPDATE invoice_lines SET tax_percent = -1").update()).hasMessageContaining("invoice_lines_tax_range");
    }
}
