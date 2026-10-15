package com.mediqo.pharmacy;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.everyItem;
import static org.hamcrest.Matchers.is;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: an optional ?form= filter (any case). The SQL may grow an "AND form = ?" only when a form is given:
 * fixed fragments of SQL, values always as parameters. An unknown form is a 400, before the database is asked.
 */
class FormFilterChallengeTest extends ApiTest {

    @Test
    void theFormNarrowsTheSearch() throws Exception {
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/medicines").param("name", "para").param("form", "syrup"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.results[*].strength", contains("125 mg/5 ml")));
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/medicines").param("name", "para").param("form", "TABLET"))
                .andExpect(jsonPath("$.results[*].form", everyItem(is("TABLET"))))
                .andExpect(jsonPath("$.results.length()").value(2));
    }

    @Test
    void anUnknownFormIs400() throws Exception {
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/medicines").param("name", "para").param("form", "TABLET' OR 1=1 --"))
                .andExpect(status().isBadRequest());
    }
}
