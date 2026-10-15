package com.billora.invoicing;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The HTTP contract: create, replace lines, read; valid, invalid and not found. */
class InvoiceContractTest extends ApiTest {

    @Test
    void anInvoiceIsCreatedWithItsLinesAndTotal() throws Exception {
        create(INVOICE).andExpect(status().isCreated()).andExpect(header().string("Location", "/invoices/1"))
                .andExpect(content().json("""
                        {"id":1,"customerName":"Kaveri Textiles Pvt Ltd","totalPaise":1399900,"lines":[
                          {"description":"Cloud hosting, March 2026","quantity":1,"unitPricePaise":499900,"amountPaise":499900},
                          {"description":"Support hours","quantity":6,"unitPricePaise":150000,"amountPaise":900000}]}"""));
        mvc.perform(get("/invoices/1")).andExpect(status().isOk()).andExpect(jsonPath("$.totalPaise").value(1399900));
    }

    @Test
    void replacingLinesKeepsOnlyTheNewOnes() throws Exception {
        create(INVOICE);
        replaceLines(1, CORRECTED).andExpect(status().isOk()).andExpect(jsonPath("$.totalPaise").value(1099900));
        mvc.perform(get("/invoices/1"))
                .andExpect(jsonPath("$.lines[*].quantity").value(org.hamcrest.Matchers.contains(1, 4)))
                .andExpect(jsonPath("$.totalPaise").value(1099900));
        replaceLines(1, """
                {"lines":[{"description":"Cloud hosting, March 2026","quantity":1,"unitPricePaise":499900}]}""").andExpect(status().isOk());
        mvc.perform(get("/invoices/1")).andExpect(jsonPath("$.lines.length()").value(1)).andExpect(jsonPath("$.totalPaise").value(499900));
    }

    @Test
    void badInvoicesAre400() throws Exception {
        create("{\"customerName\":\"Kaveri Textiles Pvt Ltd\",\"lines\":[]}").andExpect(status().isBadRequest());
        create(INVOICE.replace("Kaveri Textiles Pvt Ltd", " ")).andExpect(status().isBadRequest());
        create(INVOICE.replace("\"quantity\":6", "\"quantity\":0")).andExpect(status().isBadRequest());
        create(INVOICE.replace("\"unitPricePaise\":150000", "\"unitPricePaise\":1500.50")).andExpect(status().isBadRequest());
        create(INVOICE.replace("\"quantity\":6,", "")).andExpect(status().isBadRequest());   // a missing int is not 0
        create(INVOICE).andExpect(status().isCreated());
        replaceLines(1, "{\"lines\":[]}").andExpect(status().isBadRequest());
        replaceLines(1, "{\"lines\":[null]}").andExpect(status().isBadRequest());
        mvc.perform(get("/invoices/1")).andExpect(jsonPath("$.totalPaise").value(1399900));   // unchanged
    }

    @Test
    void unknownInvoicesAre404() throws Exception {
        mvc.perform(get("/invoices/99")).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No invoice 99."));
        replaceLines(99, CORRECTED).andExpect(status().isNotFound());
    }
}
