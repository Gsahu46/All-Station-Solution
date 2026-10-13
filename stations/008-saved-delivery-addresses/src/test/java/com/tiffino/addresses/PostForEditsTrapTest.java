package com.tiffino.addresses;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;

import static org.hamcrest.Matchers.aMapWithSize;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * Priya edits her home address on a weak signal; the reply is lost, and the app sends the same request again.
 */
@Import(PostForEditsTrapTest.OldAddressController.class)
class PostForEditsTrapTest extends ApiTest {

    /** The "before" API: every save is a POST that adds an address to a list. Kept only in tests. */
    @RestController
    static class OldAddressController {
        private final List<Address> saved = new ArrayList<>();

        @PostMapping("/old/customers/{id}/addresses")
        synchronized Address save(@PathVariable long id, @RequestBody Address a) {
            saved.add(a);
            return a;
        }

        @GetMapping("/old/customers/{id}/addresses")
        synchronized List<Address> all(@PathVariable long id) {
            return List.copyOf(saved);
        }
    }

    @Test
    void aRetriedPostSavesTheSameAddressTwice() throws Exception {
        for (int attempt = 1; attempt <= 2; attempt++) { // attempt 1's reply was lost; attempt 2 is the app's retry
            mvc.perform(post("/old/customers/42/addresses").contentType(MediaType.APPLICATION_JSON).content(HOME))
                    .andExpect(status().isOk());
        }
        mvc.perform(get("/old/customers/42/addresses"))
                .andExpect(jsonPath("$", hasSize(2))); // the bug: two "home" addresses at checkout
    }

    @Test
    void aRetriedPutLeavesOneAddress() throws Exception {
        putAddress(42, "home", HOME).andExpect(status().isCreated());
        putAddress(42, "home", HOME).andExpect(status().isOk());
        mvc.perform(get("/customers/42/addresses")).andExpect(jsonPath("$", aMapWithSize(1)));
    }
}
