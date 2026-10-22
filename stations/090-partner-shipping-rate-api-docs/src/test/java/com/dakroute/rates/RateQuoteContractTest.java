package com.dakroute.rates;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class RateQuoteContractTest extends ApiTest {

    static String parcel(String from, String to, int grams, int l, int w, int h, String service) {
        return "{\"fromPincode\":\"%s\",\"toPincode\":\"%s\",\"weightGrams\":%d,\"lengthCm\":%d,\"widthCm\":%d,\"heightCm\":%d,\"service\":\"%s\"}"
                .formatted(from, to, grams, l, w, h, service);
    }

    @Test
    void aNationalParcelIsPricedBySlabWithGst() throws Exception {
        quote(parcel("560001", "110001", 1200, 30, 20, 10, "STANDARD")).andExpect(status().isOk()).andExpect(content().json("""
                {"zone":"NATIONAL","chargeableWeightGrams":1200,"pricePaise":22500,"gstPaise":4050,"totalPaise":26550,"estimatedDays":5}"""));
    }

    @Test
    void zonesVolumetricWeightAndExpress() throws Exception {
        quote(parcel("560001", "560034", 800, 60, 40, 40, "EXPRESS")).andExpect(content().json("""
                {"zone":"LOCAL","chargeableWeightGrams":19200,"pricePaise":234000,"gstPaise":42120,"totalPaise":276120,"estimatedDays":1}"""));
        quote(parcel("560001", "563101", 500, 10, 10, 10, "STANDARD")).andExpect(jsonPath("$.zone").value("REGIONAL")).andExpect(jsonPath("$.pricePaise").value(5500));
        quote(parcel("560001", "563101", 501, 10, 10, 10, "STANDARD")).andExpect(jsonPath("$.pricePaise").value(11000));   // a started slab counts
        quote(parcel("560001", "110001", 100, 10, 10, 10, "EXPRESS")).andExpect(jsonPath("$.pricePaise").value(11250)).andExpect(jsonPath("$.gstPaise").value(2025));
    }

    @Test
    void gstIsRoundedToTheNearestPaisa() {
        // The demo tariff's prices give whole paise of GST; any future price must still round, not cut.
        assertThat(RateCard.gstPaise(1001)).isEqualTo(180);   // 180.18
        assertThat(RateCard.gstPaise(1003)).isEqualTo(181);   // 180.54
        assertThat(RateCard.gstPaise(22500)).isEqualTo(4050);
    }

    @Test
    void whatTheNetworkCannotCarryIs422() throws Exception {
        quote(parcel("560001", "110001", 50000, 10, 10, 10, "STANDARD")).andExpect(status().isOk());
        quote(parcel("560001", "110001", 50001, 10, 10, 10, "STANDARD")).andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.detail").value("Parcels above 50000 g cannot be carried"));
        quote(parcel("560001", "744101", 500, 10, 10, 10, "STANDARD")).andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.detail").value("This PIN code is not served yet"));
    }

    @Test
    void badRequestsAre400() throws Exception {
        quote(parcel("056001", "110001", 500, 10, 10, 10, "STANDARD")).andExpect(status().isBadRequest());
        quote(parcel("560001", "11001", 500, 10, 10, 10, "STANDARD")).andExpect(status().isBadRequest());
        quote(parcel("560001", "110001", 0, 10, 10, 10, "STANDARD")).andExpect(status().isBadRequest());
        quote(parcel("560001", "110001", 500, 151, 10, 10, "STANDARD")).andExpect(status().isBadRequest());
        quote(parcel("560001", "110001", 500, 10, 10, 10, "OVERNIGHT")).andExpect(status().isBadRequest());
        quote("{\"fromPincode\":\"560001\",\"toPincode\":\"110001\",\"weightGrams\":1.5,\"lengthCm\":10,\"widthCm\":10,\"heightCm\":10,\"service\":\"STANDARD\"}").andExpect(status().isBadRequest());
    }
}
