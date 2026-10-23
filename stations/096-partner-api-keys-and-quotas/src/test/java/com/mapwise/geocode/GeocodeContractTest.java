package com.mapwise.geocode;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class GeocodeContractTest extends ApiTest {

    @Test
    void aKnownAddressIsFoundWhateverItsCaseAndSpacing() throws Exception {
        geocode(ZOOMKART, "MG Road, Bengaluru").andExpect(status().isOk())
                .andExpect(content().json("{\"address\":\"MG Road, Bengaluru, Karnataka\",\"lat\":12.9756,\"lng\":77.605}", org.springframework.test.json.JsonCompareMode.STRICT));
        geocode(ZOOMKART, "  mg   ROAD,  bengaluru ").andExpect(status().isOk()).andExpect(jsonPath("$.address").value("MG Road, Bengaluru, Karnataka"));
    }

    @Test
    void unknownAddressesAre404AndBadOnes400() throws Exception {
        geocode(ZOOMKART, "Nowhere Lane, Atlantis").andExpect(status().isNotFound())
                .andExpect(jsonPath("$.detail").value("No place found for this address."));
        geocode(ZOOMKART, "MG").andExpect(status().isBadRequest());
        geocode(ZOOMKART, "x".repeat(201)).andExpect(status().isBadRequest());
        mvc.perform(get("/geocode").header("X-Api-Key", ZOOMKART)).andExpect(status().isBadRequest());
        mvc.perform(get("/geocode/").header("X-Api-Key", ZOOMKART).param("address", "MG Road, Bengaluru")).andExpect(status().isNotFound());
    }

    @Test
    void aPartnerReadsItsOwnLimitsAndWhatIsLeft() throws Exception {
        answer(CHALO);
        answer(CHALO);
        mvc.perform(get("/partners/2/usage").header("X-Api-Key", CHALO)).andExpect(status().isOk())
                .andExpect(content().json("""
                        {"partnerId":2,"partner":"Chalo Rides (trial)","perSecond":1,"burst":3,"tokensLeft":0,"dailyQuota":20,"usedToday":3,
                         "quotaResetsAt":"2026-10-27T00:00:00Z"}""".replace("2026-10-27", CLOCK.instant().plusSeconds(86400).toString().substring(0, 10)),
                        org.springframework.test.json.JsonCompareMode.STRICT));   // the usage call itself is the third
    }
}
