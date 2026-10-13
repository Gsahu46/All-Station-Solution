package com.fitnest.classes;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: a trainer changes a class's capacity with PATCH /classes/{id}. */
class CapacityChangeChallengeTest extends ApiTest {

    ResultActions setCapacity(long classId, String json) throws Exception {
        return mvc.perform(patch("/classes/{id}", classId).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    @AfterEach
    void restoreZumba() throws Exception {
        schedule.clearBookings();
        setCapacity(3, "{\"capacity\":15}");
    }

    @Test
    void raisingOrLoweringCapacityIs200WithTheUpdatedClass() throws Exception {
        book(3, 101);
        setCapacity(3, "{\"capacity\":5}")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.capacity").value(5))
                .andExpect(jsonPath("$.spotsLeft").value(4));
    }

    @Test
    void capacityBelowTheCurrentBookingsIs409AndNothingChanges() throws Exception {
        book(3, 101);
        book(3, 102);
        setCapacity(3, "{\"capacity\":1}")
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.title").value("Capacity below bookings"));
        setCapacity(3, "{\"capacity\":15}").andExpect(jsonPath("$.spotsLeft").value(13));
    }

    @Test
    void capacityOutsideOneToFiftyIs400() throws Exception {
        setCapacity(3, "{\"capacity\":0}").andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.capacity").exists());
        setCapacity(3, "{\"capacity\":51}").andExpect(status().isBadRequest());
        setCapacity(3, "{}").andExpect(status().isBadRequest());
    }

    @Test
    void anUnknownClassIs404() throws Exception {
        setCapacity(999, "{\"capacity\":10}").andExpect(status().isNotFound());
    }
}
