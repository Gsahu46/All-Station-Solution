package com.kartwala.categories;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: PUT /categories/{id}/parent {"parentId": 2} moves a category with everything under it and answers its
 * new breadcrumb. A move under its own descendant is 409 (the database's categories_no_cycle refuses it); an unknown
 * category or parent is 404.
 */
class MoveCategoryChallengeTest extends ApiTest {

    @AfterEach
    void putPhonesBack() {
        jdbc.sql("UPDATE categories SET parent_id = 2 WHERE id = 3").update();
    }

    @Test
    void aMoveTakesTheWholeBranch() throws Exception {
        mvc.perform(put("/categories/3/parent").contentType(MediaType.APPLICATION_JSON).content("{\"parentId\": 1}")).andExpect(status().isOk())
                .andExpect(jsonPath("$.path").value("Home > Phones"));
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/categories/4/breadcrumb"))
                .andExpect(jsonPath("$.path").value("Home > Phones > Android"));
    }

    @Test
    void aLoopIs409AndUnknownIs404() throws Exception {
        mvc.perform(put("/categories/2/parent").contentType(MediaType.APPLICATION_JSON).content("{\"parentId\": 4}")).andExpect(status().isConflict());
        mvc.perform(put("/categories/2/parent").contentType(MediaType.APPLICATION_JSON).content("{\"parentId\": 999}")).andExpect(status().isNotFound());
        mvc.perform(put("/categories/999/parent").contentType(MediaType.APPLICATION_JSON).content("{\"parentId\": 1}")).andExpect(status().isNotFound());
    }
}
