package com.tiffino.addresses;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 2: PUT /customers/{id}/default-address {"label": "..."}: one default at a time, safe to repeat. */
class DefaultAddressChallengeTest extends ApiTest {

    ResultActions setDefault(String label) throws Exception {
        return mvc.perform(put("/customers/42/default-address").contentType(MediaType.APPLICATION_JSON)
                .content("{\"label\":\"" + label + "\"}"));
    }

    @Test
    void settingTheDefaultTwiceGivesTheSameAnswer() throws Exception {
        putAddress(42, "home", HOME);
        setDefault("home").andExpect(status().isOk()).andExpect(jsonPath("$.label").value("home"));
        setDefault("HOME").andExpect(status().isOk()).andExpect(jsonPath("$.label").value("home"));
        mvc.perform(get("/customers/42/default-address")).andExpect(jsonPath("$.label").value("home"));
    }

    @Test
    void thereIsOnlyOneDefault() throws Exception {
        putAddress(42, "home", HOME);
        putAddress(42, "work", HOME);
        setDefault("home");
        setDefault("work");
        mvc.perform(get("/customers/42/default-address")).andExpect(jsonPath("$.label").value("work"));
    }

    @Test
    void aLabelWithNoAddressIs409() throws Exception {
        setDefault("gym").andExpect(status().isConflict());
    }

    @Test
    void deletingTheDefaultAddressClearsTheDefault() throws Exception {
        putAddress(42, "home", HOME);
        setDefault("home");
        deleteAddress(42, "home");
        mvc.perform(get("/customers/42/default-address")).andExpect(status().isNotFound());
    }
}
