package com.dakroute.fleet;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.hasItems;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 1: Dakroute buys a CNG cargo van (vehicle 6, KA01CN2468, Bajaj Maxima Cargo CNG, 51,000 km).
 * A CNG engine needs an oil change every 10,000 km, a gas leak check every 10,000 km and a cylinder hydro-test
 * every 1,00,000 km. Add it, and prove no other vehicle's plan changed.
 */
class CngPowertrainChallengeTest extends ApiTest {

    @Test
    void theCngVanGetsCngAndVanTasks() throws Exception {
        mvc.perform(get("/fleet/vehicles/6/service-plan"))
                .andExpect(jsonPath("$.powertrain").value("CNG"))
                .andExpect(jsonPath("$.body").value("VAN"))
                .andExpect(jsonPath("$.tasks[*].task", hasItems("Gas leak check", "Cylinder hydro-test", "Engine oil change", "Brake check")));
    }

    @Test
    void theOtherVehiclesAreUntouched() throws Exception {
        mvc.perform(get("/fleet/vehicles/2/service-plan"))
                .andExpect(jsonPath("$.tasks[*].task", contains("Brake check", "Engine oil change", "Tyre rotation", "Spark plugs")));
    }
}
