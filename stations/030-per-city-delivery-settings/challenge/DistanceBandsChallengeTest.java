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
 * Challenge 2: optional fee bands per city, replacing the flat fee: up to 3 km Rs 15, up to 6 km Rs 30. Bands must be
 * in increasing distance and the last must reach the city's radius, or the app does not start.
 */
@SpringBootTest(properties = {
        "basketo.cities.pune.fee-bands[0].up-to-km=3.0", "basketo.cities.pune.fee-bands[0].fee-paise=1500",
        "basketo.cities.pune.fee-bands[1].up-to-km=6.0", "basketo.cities.pune.fee-bands[1].fee-paise=3000"})
@AutoConfigureMockMvc
class DistanceBandsChallengeTest {

    @Autowired
    MockMvc mvc;

    @Test
    void theFeeDependsOnTheServersDistance() throws Exception {
        String at = "{\"city\":\"pune\",\"lat\":%s,\"lon\":%s,\"orderPaise\":25000}";
        mvc.perform(post("/delivery-checks").contentType(MediaType.APPLICATION_JSON).content(at.formatted("18.5362", "73.8940")))   // 4.94 km
                .andExpect(jsonPath("$.feePaise").value(3000));
        mvc.perform(post("/delivery-checks").contentType(MediaType.APPLICATION_JSON).content(at.formatted("18.5308", "73.8575")))   // about 1 km
                .andExpect(jsonPath("$.feePaise").value(1500));
    }

    @Test
    void bandsThatStopShortOfTheRadiusStopTheAppStarting() {
        ConfigRunner.settings("basketo.cities.pune.minimum-order-paise=14900",
                        "basketo.cities.pune.fee-bands[0].up-to-km=3.0", "basketo.cities.pune.fee-bands[0].fee-paise=1500")
                .run(c -> assertThat(c).hasFailed().getFailure().hasStackTraceContaining("feeBandsCoverTheRadius"));
    }
}
