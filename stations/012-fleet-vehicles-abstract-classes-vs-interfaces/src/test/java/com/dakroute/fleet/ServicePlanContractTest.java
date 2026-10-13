package com.dakroute.fleet;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: plans for different combinations of parts, soonest first, and the refusals. */
class ServicePlanContractTest extends ApiTest {

    @Test
    void aDieselTruckGetsEngineAndTruckTasksSoonestFirst() throws Exception {
        mvc.perform(get("/fleet/vehicles/1/service-plan"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.registration").value("KA01TR1234"))
                .andExpect(jsonPath("$.powertrain").value("DIESEL"))
                .andExpect(jsonPath("$.body").value("TRUCK"))
                .andExpect(jsonPath("$.odometerKm").value(128400))
                .andExpect(jsonPath("$.tasks[*].task", contains("Axle greasing", "Brake check", "Engine oil change",
                        "Tyre rotation", "Fuel filter", "Diesel particulate filter clean")))
                .andExpect(jsonPath("$.tasks[2].nextDueKm").value(135000))
                .andExpect(jsonPath("$.tasks[2].dueInKm").value(6600));
    }

    @Test
    void anElectricVanGetsBatteryAndVanTasks() throws Exception {
        mvc.perform(get("/fleet/vehicles/3/service-plan"))
                .andExpect(jsonPath("$.tasks[*].task", contains("Battery health check", "Tyre rotation", "Brake check", "Battery coolant")))
                .andExpect(jsonPath("$.tasks[0].dueInKm").value(1050))
                .andExpect(jsonPath("$.tasks[0].dueSoon").value(true))    // within 10% of 20,000 km
                .andExpect(jsonPath("$.tasks[1].dueSoon").value(false));  // 1,050 is not within 10% of 10,000
    }

    @Test
    void aPetrolBikeGetsEngineAndTwoWheelerTasks() throws Exception {
        mvc.perform(get("/fleet/vehicles/4/service-plan"))
                .andExpect(jsonPath("$.tasks[*].task", contains("Brake check", "Chain lubrication", "Engine oil change", "Spark plugs")))
                .andExpect(jsonPath("$.tasks[2].everyKm").value(10000));  // petrol oil interval, not diesel's 15,000
    }

    @Test
    void anUnknownVehicleIs404AndANonNumberIs400() throws Exception {
        mvc.perform(get("/fleet/vehicles/99/service-plan")).andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Vehicle not found"));
        mvc.perform(get("/fleet/vehicles/truck/service-plan")).andExpect(status().isBadRequest());
    }
}
