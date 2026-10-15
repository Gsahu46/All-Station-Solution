package com.basketo.delivery;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.hamcrest.Matchers.empty;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: a city's terms, checks the server works out itself, and every refusal. */
@SpringBootTest
@AutoConfigureMockMvc
class DeliveryContractTest {

    @Autowired
    MockMvc mvc;

    ResultActions check(String json) throws Exception {
        return mvc.perform(post("/delivery-checks").contentType(MediaType.APPLICATION_JSON).content(json));
    }

    @Test
    void aCitysTermsComeFromConfiguration() throws Exception {
        mvc.perform(get("/cities/Pune/delivery-terms"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.city").value("pune"))
                .andExpect(jsonPath("$.radiusKm").value(6.0))
                .andExpect(jsonPath("$.feePaise").value(2500))
                .andExpect(jsonPath("$.minimumOrderPaise").value(14900));
    }

    @Test
    void anAddressInsideTheRadiusIsDeliverable() throws Exception {
        check("{\"city\":\"pune\",\"lat\":18.5362,\"lon\":73.8940,\"orderPaise\":25000}")   // Koregaon Park
                .andExpect(jsonPath("$.distanceKm").value(4.94))
                .andExpect(jsonPath("$.deliverable").value(true))
                .andExpect(jsonPath("$.reasons", empty()));
    }

    @Test
    void theServerSaysTooFarAndTooSmallWhateverTheClientThinks() throws Exception {
        check("{\"city\":\"pune\",\"lat\":18.5913,\"lon\":73.7389,\"orderPaise\":9900}")      // Hinjewadi, Rs 99
                .andExpect(jsonPath("$.distanceKm").value(13.28))
                .andExpect(jsonPath("$.deliverable").value(false))
                .andExpect(jsonPath("$.reasons[0]").value("OUT_OF_RANGE"))
                .andExpect(jsonPath("$.reasons[1]").value("BELOW_MINIMUM"));
        check("{\"city\":\"pune\",\"lat\":18.5913,\"lon\":73.7389,\"orderPaise\":25000,\"distanceKm\":0}")
                .andExpect(status().isBadRequest());   // a client-side distance is not a field any more
    }

    @Test
    void aCityWeDoNotServeIs404() throws Exception {
        mvc.perform(get("/cities/jaipur/delivery-terms")).andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("City not served"));
        check("{\"city\":\"jaipur\",\"lat\":26.9,\"lon\":75.8,\"orderPaise\":25000}").andExpect(status().isNotFound());
    }

    @Test
    void badCoordinatesOrAmountsAre400() throws Exception {
        check("{\"city\":\"pune\",\"lat\":91,\"lon\":73.8,\"orderPaise\":25000}").andExpect(status().isBadRequest());
        check("{\"city\":\"pune\",\"lat\":18.5,\"lon\":73.8,\"orderPaise\":0}").andExpect(status().isBadRequest());
        check("{\"city\":\"pune\",\"lat\":18.5,\"lon\":73.8,\"orderPaise\":250.5}").andExpect(status().isBadRequest());
        check("{\"city\":\"pune\",\"lat\":18.5,\"orderPaise\":25000}").andExpect(status().isBadRequest());
    }
}
