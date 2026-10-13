package com.seatsure.registrations;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: one registration per email per event. Letter case and spaces do not make a new person. */
class DuplicateEmailChallengeTest extends ApiTest {

    @Test
    void theSameEmailTwiceForOneEventIs409() throws Exception {
        register("pune-tech-summit-2026", """
                {"name":"Neha","email":"neha.dup@example.com","tickets":1}""").andExpect(status().isCreated());
        register("pune-tech-summit-2026", """
                {"name":"Neha S","email":"  NEHA.DUP@Example.com ","tickets":3}""")
                .andExpect(status().isConflict())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Already registered"));
    }

    @Test
    void theSameEmailForAnotherEventIsFine() throws Exception {
        register("pune-tech-summit-2026", """
                {"name":"Kabir","email":"kabir.two@example.com","tickets":1}""").andExpect(status().isCreated());
        register("goa-food-fest-2026", """
                {"name":"Kabir","email":"kabir.two@example.com","tickets":1}""").andExpect(status().isCreated());
    }
}
