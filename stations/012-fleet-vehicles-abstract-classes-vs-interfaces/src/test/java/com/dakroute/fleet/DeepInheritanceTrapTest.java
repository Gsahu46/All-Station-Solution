package com.dakroute.fleet;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasItem;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * The first test written for this station: it reproduces the problem before the fix.
 * The "before" code is a family tree of abstract classes, the way the fleet app grew.
 */
class DeepInheritanceTrapTest extends ApiTest {

    abstract static class OldVehicle {
        List<String> tasks() {
            return new ArrayList<>(List.of("Brake check"));
        }
    }

    abstract static class OldFuelVehicle extends OldVehicle {
        @Override
        List<String> tasks() {
            List<String> t = super.tasks();
            t.add("Engine oil change");
            t.add("Diesel particulate filter clean"); // added later "for the trucks", in the shared parent
            return t;
        }
    }

    static class OldVan extends OldFuelVehicle {
        @Override
        List<String> tasks() {
            List<String> t = super.tasks();
            t.add("Tyre rotation");
            return t;
        }
    }

    /** "An EV van is a van", so it extends OldVan, and inherits everything a fuel van needs. */
    static class OldEvVan extends OldVan {
        @Override
        List<String> tasks() {
            List<String> t = super.tasks();
            t.add("Battery health check");
            return t;
        }
    }

    static class OldPetrolBike extends OldFuelVehicle {
    }

    @Test
    void theEvVanInheritsAnOilChangeAndThePetrolBikeADieselFilter() {
        assertThat(new OldEvVan().tasks()).contains("Engine oil change");                 // an EV has no engine oil
        assertThat(new OldPetrolBike().tasks()).contains("Diesel particulate filter clean"); // nor does a petrol bike
    }

    @Test
    void composedVehiclesGetOnlyTheTasksOfTheirOwnParts() throws Exception {
        mvc.perform(get("/fleet/vehicles/3/service-plan"))   // Tata Ace EV: ELECTRIC + VAN
                .andExpect(jsonPath("$.tasks[*].task", hasItem("Battery health check")))
                .andExpect(jsonPath("$.tasks[*].task", not(hasItem("Engine oil change"))));
        mvc.perform(get("/fleet/vehicles/4/service-plan"))   // Hero Splendor+: PETROL + TWO_WHEELER
                .andExpect(jsonPath("$.tasks[*].task", not(hasItem("Diesel particulate filter clean"))));
    }
}
