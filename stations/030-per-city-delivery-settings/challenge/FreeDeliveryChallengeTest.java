package com.basketo.delivery;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 1: an optional basketo.cities.*.free-delivery-above-paise. Orders at or above it pay no fee. It must be
 * above the city's minimum order, or the app does not start (a rule across two fields).
 */
@SpringBootTest(properties = "basketo.cities.pune.free-delivery-above-paise=49900")
@AutoConfigureMockMvc
class FreeDeliveryChallengeTest {

    @Autowired
    MockMvc mvc;

    @Test
    void bigOrdersDeliverFree() throws Exception {
        String at = "{\"city\":\"pune\",\"lat\":18.5362,\"lon\":73.8940,\"orderPaise\":%d}";
        mvc.perform(post("/delivery-checks").contentType(MediaType.APPLICATION_JSON).content(at.formatted(49_900)))
                .andExpect(jsonPath("$.feePaise").value(0));
        mvc.perform(post("/delivery-checks").contentType(MediaType.APPLICATION_JSON).content(at.formatted(30_000)))
                .andExpect(jsonPath("$.feePaise").value(2500));
    }

    @Test
    void aThresholdBelowTheMinimumOrderStopsTheAppStarting() {
        ConfigRunner.settings("basketo.cities.pune.minimum-order-paise=14900", "basketo.cities.pune.free-delivery-above-paise=10000")
                .run(c -> assertThat(c).hasFailed().getFailure().hasStackTraceContaining("freeDeliveryAboveMinimum"));
    }
}
