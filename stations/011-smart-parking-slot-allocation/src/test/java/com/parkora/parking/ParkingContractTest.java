package com.parkora.parking;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import java.time.Duration;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: entry, exit, fees, and every way a request can be refused. */
class ParkingContractTest extends ApiTest {

    @Test
    void entryIs201WithATicketForTheNearestSlot() throws Exception {
        enter("MH12AB1234", "CAR")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.ticketId").isNotEmpty())
                .andExpect(jsonPath("$.vehicleNumber").value("MH12AB1234"))
                .andExpect(jsonPath("$.vehicleType").value("CAR"))
                .andExpect(jsonPath("$.slot.id").value("F0-C01"))
                .andExpect(jsonPath("$.slot.floor").value(0))
                .andExpect(jsonPath("$.enteredAt").value("2026-10-19T09:00:00Z"));
    }

    @Test
    void carsFillTheNearestSlotsFirstAndAFreedNearSlotIsReused() throws Exception {
        String first = ticketOf(enter("MH12AB0001", "CAR"));
        enter("MH12AB0002", "CAR").andExpect(jsonPath("$.slot.id").value("F0-C02"));
        exit(first);
        enter("MH12AB0003", "CAR").andExpect(jsonPath("$.slot.id").value("F0-C01")); // nearest again
        enter("MH12AB0004", "CAR").andExpect(jsonPath("$.slot.id").value("F0-C03"));
    }

    @Test
    void spacesHyphensAndLowerCaseInThePlateAreTheSameCar() throws Exception {
        enter("mh 12 ab-1234", "CAR").andExpect(jsonPath("$.vehicleNumber").value("MH12AB1234"));
        enter("MH12AB1234", "CAR").andExpect(status().isConflict())
                .andExpect(jsonPath("$.title").value("Already parked"))
                .andExpect(jsonPath("$.ticketId").isNotEmpty());
    }

    @Test
    void badInputIs400() throws Exception {
        enter("12345", "CAR").andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Invalid vehicle number"));
        enter("MH12AB1234", "TRUCK").andExpect(status().isBadRequest());
        mvcPostEmpty();
    }

    private void mvcPostEmpty() throws Exception {
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post("/parking/entries")
                        .contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.vehicleNumber").exists())
                .andExpect(jsonPath("$.errors.vehicleType").exists());
    }

    @Test
    void whenCarSlotsRunOutCarsGet409ButBikesStillEnter() throws Exception {
        for (int i = 0; i < Garage.FLOORS * Garage.CAR_SLOTS_PER_FLOOR; i++) {
            garage.enter("MH12AB%04d".formatted(i), VehicleType.CAR);
        }
        enter("MH12ZZ9999", "CAR").andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("No free slot"));
        enter("MH12ZZ9998", "BIKE").andExpect(status().isCreated());
    }

    @Test
    void exitChargesEveryStartedHour() throws Exception {
        String car = ticketOf(enter("MH12AB1234", "CAR"));
        clock.advance(Duration.ofMinutes(150));
        exit(car).andExpect(status().isOk())
                .andExpect(jsonPath("$.minutesParked").value(150))
                .andExpect(jsonPath("$.hoursCharged").value(3))
                .andExpect(jsonPath("$.feePaise").value(4000 + 2 * 3000))
                .andExpect(jsonPath("$.slotId").value("F0-C01"));
    }

    @Test
    void aShortBikeStayPaysTheFirstHour() throws Exception {
        String bike = ticketOf(enter("KA05XY4321", "BIKE"));
        clock.advance(Duration.ofMinutes(12));
        exit(bike).andExpect(jsonPath("$.hoursCharged").value(1)).andExpect(jsonPath("$.feePaise").value(2000));
    }

    @Test
    void exitingTwiceReturnsTheSameReceiptAndFreesTheSlotOnce() throws Exception {
        String car = ticketOf(enter("MH12AB1234", "CAR"));
        clock.advance(Duration.ofMinutes(30));
        String first = exit(car).andReturn().getResponse().getContentAsString();
        int freeAfterOne = garage.freeCount(SlotType.CAR);
        clock.advance(Duration.ofHours(5));                       // the gate retries much later
        String second = exit(car).andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        assertThat(second).isEqualTo(first);
        assertThat(garage.freeCount(SlotType.CAR)).isEqualTo(freeAfterOne);
    }

    @Test
    void theSameCarCanParkAgainAfterLeaving() throws Exception {
        exit(ticketOf(enter("MH12AB1234", "CAR")));
        enter("MH12AB1234", "CAR").andExpect(status().isCreated());
    }

    @Test
    void anUnknownOrMalformedTicketIsRefused() throws Exception {
        exit(UUID.randomUUID().toString()).andExpect(status().isNotFound()).andExpect(jsonPath("$.title").value("Ticket not found"));
        exit("not-a-ticket").andExpect(status().isBadRequest());
    }
}
