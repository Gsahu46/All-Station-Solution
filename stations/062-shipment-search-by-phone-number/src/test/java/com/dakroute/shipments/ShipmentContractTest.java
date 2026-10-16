package com.dakroute.shipments;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class ShipmentContractTest extends ApiTest {

    @Test
    void aCustomersShipmentsInTheRangeNewestFirst() throws Exception {
        mvc.perform(get("/shipments/search").param("phone", CUSTOMER).param("from", "2026-03-01").param("to", "2026-03-31")).andExpect(status().isOk())
                .andExpect(jsonPath("$.phone").value(CUSTOMER)).andExpect(jsonPath("$.from").value("2026-03-01")).andExpect(jsonPath("$.to").value("2026-03-31"))
                .andExpect(jsonPath("$.shipments[*].awb", contains("DR1000000002", "DR1000000001")))
                .andExpect(jsonPath("$.shipments[0].bookedOn").value("2026-03-15")).andExpect(jsonPath("$.shipments[0].status").value("RETURNED"));
    }

    @Test
    void thePhoneCanBeTypedTheWaysCustomersSayIt() throws Exception {
        for (String typed : new String[]{"+91 98765 43210", "098765-43210", "(98765) 43210"}) {
            mvc.perform(get("/shipments/search").param("phone", typed).param("from", "2026-01-01").param("to", "2026-12-31")).andExpect(status().isOk())
                    .andExpect(jsonPath("$.phone").value(CUSTOMER)).andExpect(jsonPath("$.shipments", hasSize(3)));
        }
    }

    @Test
    void theBusySellerGetsTheNewestFifty() throws Exception {
        mvc.perform(get("/shipments/search").param("phone", SELLER).param("from", "2026-01-01").param("to", "2026-09-30")).andExpect(status().isOk())
                .andExpect(jsonPath("$.shipments", hasSize(50))).andExpect(jsonPath("$.shipments[0].bookedOn").value("2026-09-30"));
    }

    @Test
    void noShipmentIsAnEmptyList() throws Exception {
        mvc.perform(get("/shipments/search").param("phone", "7000000000").param("from", "2026-01-01").param("to", "2026-12-31")).andExpect(status().isOk())
                .andExpect(jsonPath("$.shipments", empty()));
        mvc.perform(get("/shipments/search").param("phone", CUSTOMER).param("from", "2026-04-01").param("to", "2026-04-30")).andExpect(status().isOk())
                .andExpect(jsonPath("$.shipments", empty()));
    }

    @Test
    void badSearchesAre400() throws Exception {
        String[][] bad = {
                {"12345", "2026-03-01", "2026-03-31"},           // not a mobile number
                {"5876543210", "2026-03-01", "2026-03-31"},      // Indian mobiles start with 6 to 9
                {"9876543210' OR '1'='1", "2026-03-01", "2026-03-31"},
                {CUSTOMER, "2026-03-31", "2026-03-01"},          // backwards
                {CUSTOMER, "2025-01-01", "2026-03-31"},          // more than 366 days
                {CUSTOMER, "01-03-2026", "2026-03-31"},          // not ISO
        };
        for (String[] b : bad) {
            mvc.perform(get("/shipments/search").param("phone", b[0]).param("from", b[1]).param("to", b[2])).andExpect(status().isBadRequest());
        }
        mvc.perform(get("/shipments/search").param("phone", CUSTOMER).param("from", "2026-03-01")).andExpect(status().isBadRequest());
    }
}
