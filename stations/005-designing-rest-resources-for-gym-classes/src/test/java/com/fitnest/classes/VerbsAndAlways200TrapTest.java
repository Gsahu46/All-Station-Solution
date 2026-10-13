package com.fitnest.classes;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the problem before the fix.
 * Three different things go wrong; the old API answers all three the same way.
 */
@Import(VerbsAndAlways200TrapTest.OldBookingController.class)
class VerbsAndAlways200TrapTest extends ApiTest {

    /** The "before" API: verbs in the URL, everything in query parameters, and 200 whatever happens. */
    @RestController
    static class OldBookingController {
        private final ClassSchedule schedule;

        OldBookingController(ClassSchedule schedule) {
            this.schedule = schedule;
        }

        @PostMapping("/bookClass")
        Map<String, Object> bookClass(@RequestParam long classId, @RequestParam long memberId) {
            return switch (schedule.book(classId, memberId)) {
                case BookingOutcome.Booked b -> Map.of("success", true, "message", "Booked");
                default -> Map.of("success", false, "message", "Could not book");
            };
        }
    }

    @Test
    void theOldApiAnswers200ForAFullClassAnUnknownClassAndADoubleBooking() throws Exception {
        mvc.perform(post("/bookClass").param("classId", "1").param("memberId", "101")).andExpect(status().isOk());
        mvc.perform(post("/bookClass").param("classId", "1").param("memberId", "102")).andExpect(status().isOk());

        // Three different problems, one answer. The app cannot tell "full" (try another class)
        // from "already yours" (nothing to do) from "no such class" (refresh the timetable).
        for (String[] attempt : new String[][]{{"1", "103"}, {"1", "101"}, {"999", "101"}}) {
            mvc.perform(post("/bookClass").param("classId", attempt[0]).param("memberId", attempt[1]))
                    .andExpect(status().isOk())
                    .andExpect(jsonPath("$.success").value(false))
                    .andExpect(jsonPath("$.message").value("Could not book"));
        }
    }

    @Test
    void theResourceApiGivesEachOutcomeItsOwnStatus() throws Exception {
        book(1, 101).andExpect(status().isCreated());
        book(1, 102).andExpect(status().isCreated());

        book(1, 103).andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Class is full"));
        book(1, 101).andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Already booked"));
        book(999, 101).andExpect(status().isNotFound()).andExpect(jsonPath("$.title").value("Class not found"));
    }
}
