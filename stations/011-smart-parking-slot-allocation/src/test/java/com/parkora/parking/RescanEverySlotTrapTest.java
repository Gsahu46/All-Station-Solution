package com.parkora.parking;

import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * An empty building; a bike arrives, then a car.
 */
class RescanEverySlotTrapTest extends ApiTest {

    /** The "before" allocator: walk the slot sheet from the top and take the first free slot. Kept only in tests. */
    static class OldAllocator {
        final List<Slot> sheet = Garage.layout();
        final Set<String> taken = new HashSet<>();
        int slotsLookedAt;

        Slot allocate() {
            for (Slot s : sheet) {
                slotsLookedAt++;
                if (taken.add(s.id())) {
                    return s;
                }
            }
            return null;
        }
    }

    @Test
    void scanningTheSheetSendsTheBikeToACarSlotOnTheTopFloor() {
        OldAllocator old = new OldAllocator();
        Slot forBike = old.allocate();
        Slot forCar = old.allocate();
        assertThat(forBike.type()).isEqualTo(SlotType.CAR);          // a bike in a car slot
        assertThat(forBike.floor()).isEqualTo(5);                     // on the top floor of an empty building
        assertThat(forCar.walkMetres()).isEqualTo(5 * 80 + 2 * 6);    // the car walks 412 m, not 6 m

        // and every entry re-reads the sheet: filling the building looks at 360 + 359 + ... + 1 slots
        for (int i = 2; i < 360; i++) {
            old.allocate();
        }
        assertThat(old.slotsLookedAt).isEqualTo(360 * 361 / 2);
    }

    @Test
    void theGarageGivesEachVehicleTheNearestSlotOfItsOwnType() throws Exception {
        enter("KA01AB0001", "BIKE").andExpect(jsonPath("$.slot.id").value("F0-B01"))
                .andExpect(jsonPath("$.slot.type").value("BIKE"));
        enter("KA01AB0002", "CAR").andExpect(jsonPath("$.slot.id").value("F0-C01"))
                .andExpect(jsonPath("$.slot.walkMetres").value(6));
    }
}
