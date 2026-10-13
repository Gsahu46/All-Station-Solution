package com.seatsure.registrations;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * Someone submits the form with an empty name, "asha" as the email, and 0 tickets.
 */
@Import(TrustingTheClientTrapTest.NaiveRegistrationController.class)
class TrustingTheClientTrapTest extends ApiTest {

    static final String GARBAGE = """
            {"name":"   ","email":"asha","tickets":0}
            """;

    /** The "before" code: the same store, but no @Valid. It trusts that the form already checked everything. */
    @RestController
    static class NaiveRegistrationController {
        private final RegistrationStore store;

        NaiveRegistrationController(RegistrationStore store) {
            this.store = store;
        }

        @PostMapping("/naive/events/{eventId}/registrations")
        Registration register(@PathVariable String eventId, @RequestBody RegistrationRequest request) {
            return store.save(eventId, request);
        }
    }

    @Test
    void withoutValidationGarbageIsSavedAndTheOrganiserExportsIt() throws Exception {
        int before = store.count();
        mvc.perform(post("/naive/events/pune-tech-summit-2026/registrations").contentType(MediaType.APPLICATION_JSON).content(GARBAGE))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value(""))       // the bug: a nameless registration
                .andExpect(jsonPath("$.email").value("asha"))   // nobody can be emailed
                .andExpect(jsonPath("$.tickets").value(0));     // a registration for no seats
        assertThat(store.count()).isEqualTo(before + 1);
    }

    @Test
    void withValidationTheSameRequestIs400AndNothingIsSaved() throws Exception {
        int before = store.count();
        register("pune-tech-summit-2026", GARBAGE)
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.name").value("must not be blank"))
                .andExpect(jsonPath("$.errors.email").value("must be an email address like name@example.com"))
                .andExpect(jsonPath("$.errors.tickets").value("must be greater than or equal to 1"));
        assertThat(store.count()).isEqualTo(before);
    }
}
