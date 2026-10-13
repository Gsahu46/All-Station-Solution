package com.basketo.stores;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * The app asks about a store id that does not exist (a typo, a store that was shut down, an old app version).
 */
@Import(UnknownStoreTrapTest.NaiveStoreController.class)
class UnknownStoreTrapTest extends ApiTest {

    /** The "before" code: returns whatever the lookup gives, even null. Kept only in tests, to show the trap. */
    @RestController
    static class NaiveStoreController {
        private final StoreDirectory directory;

        NaiveStoreController(StoreDirectory directory) {
            this.directory = directory;
        }

        @GetMapping("/naive/stores/{storeId}/status")
        StoreStatus status(@PathVariable String storeId) {
            return directory.find(storeId).orElse(null);
        }
    }

    @Test
    void naiveVersionAnswers200WithAnEmptyBodyForAStoreThatDoesNotExist() throws Exception {
        mvc.perform(get("/naive/stores/BLR-XYZ-99/status"))
                .andExpect(status().isOk())                 // the bug: "OK" for a store that does not exist
                .andExpect(content().string(""));           // and nothing the app can read
    }

    @Test
    void fixedVersionAnswers404WithAProblemBody() throws Exception {
        mvc.perform(get("/stores/BLR-XYZ-99/status"))
                .andExpect(status().isNotFound())
                .andExpect(content().contentType("application/problem+json"));
    }
}
