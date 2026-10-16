package com.kartwala.prices;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class PriceContractTest extends ApiTest {

    @Test
    void thePriceNow() throws Exception {
        mvc.perform(get("/products/1/price")).andExpect(status().isOk())
                .andExpect(jsonPath("$.pricePaise").value(49900)).andExpect(jsonPath("$.at").value("2026-10-16T11:30:00+05:30"))
                .andExpect(jsonPath("$.validFrom").value("2026-01-01T00:00:00+05:30")).andExpect(jsonPath("$.validTo").doesNotExist());
    }

    @Test
    void theSaleStartsAtMidnightInIndiaWhateverOffsetTheQuestionUses() throws Exception {
        priceAt(2, "2026-11-07T23:59:59+05:30").andExpect(jsonPath("$.pricePaise").value(19900));
        priceAt(2, "2026-11-08T00:00:00+05:30").andExpect(jsonPath("$.pricePaise").value(14900))
                .andExpect(jsonPath("$.validFrom").value("2026-11-08T00:00:00+05:30")).andExpect(jsonPath("$.validTo").value("2026-11-11T00:00:00+05:30"));
        priceAt(2, "2026-11-07T18:30:00Z").andExpect(jsonPath("$.pricePaise").value(14900));        // the same instant, in UTC
        priceAt(2, "2026-11-11T00:00:00+05:30").andExpect(jsonPath("$.pricePaise").value(19900));   // the end is not part of the sale
    }

    @Test
    void pastPricesAreKept() throws Exception {
        priceAt(3, "2026-03-01T12:00:00+05:30").andExpect(status().isOk()).andExpect(jsonPath("$.pricePaise").value(89900));
    }

    @Test
    void aSaleCutsTheBasePriceInTwo() throws Exception {
        setPrice(1, 39900, "2026-11-08T00:00", "2026-11-11T00:00").andExpect(status().isCreated())
                .andExpect(jsonPath("$.windows[*].pricePaise", contains(49900, 39900, 49900)))
                .andExpect(jsonPath("$.windows[*].from", contains("2026-01-01T00:00:00+05:30", "2026-11-08T00:00:00+05:30", "2026-11-11T00:00:00+05:30")))
                .andExpect(jsonPath("$.windows[2].to").doesNotExist());
    }

    @Test
    void aFlashSaleInsideTheSale() throws Exception {
        setPrice(2, 12900, "2026-11-09T00:00", "2026-11-10T00:00").andExpect(status().isCreated())
                .andExpect(jsonPath("$.windows[*].pricePaise", contains(19900, 14900, 12900, 14900, 19900)));
    }

    @Test
    void aWindowCoveringTheWholeSaleReplacesIt() throws Exception {
        setPrice(2, 17900, "2026-11-07T00:00", "2026-11-12T00:00").andExpect(status().isCreated())
                .andExpect(jsonPath("$.windows[*].pricePaise", contains(19900, 17900, 19900)))
                .andExpect(jsonPath("$.windows[2].from").value("2026-11-12T00:00:00+05:30"));
    }

    @Test
    void aNewPriceFromThenOnReplacesEverythingAfter() throws Exception {
        setPrice(2, 24900, "2026-11-10T00:00", null).andExpect(status().isCreated())
                .andExpect(jsonPath("$.windows[*].pricePaise", contains(19900, 14900, 24900)))
                .andExpect(jsonPath("$.windows[1].to").value("2026-11-10T00:00:00+05:30")).andExpect(jsonPath("$.windows[2].to").doesNotExist());
    }

    @Test
    void thePastCannotChangeAndOtherMistakes() throws Exception {
        setPrice(1, 39900, "2026-10-01T00:00", null).andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.detail").value("Prices in the past are history and cannot change"));
        setPrice(1, 39900, "2026-11-08T00:00", "2026-11-08T00:00").andExpect(status().isBadRequest());
        setPrice(1, 50, "2026-11-08T00:00", null).andExpect(status().isBadRequest());
        setPrice(99, 39900, "2026-11-08T00:00", null).andExpect(status().isNotFound());
        priceAt(99, "2026-11-08T00:00:00+05:30").andExpect(status().isNotFound());
        priceAt(1, "2025-06-01T00:00:00+05:30").andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("Product 1 has no price at 2025-06-01T00:00+05:30"));
        priceAt(1, "8 November").andExpect(status().isBadRequest());
    }
}
