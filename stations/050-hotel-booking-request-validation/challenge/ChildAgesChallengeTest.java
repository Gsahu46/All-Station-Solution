package com.ghoomo.bookings;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: with children, the request carries "childAges", one age (0 to 17) per child. An age out of range is a
 * broken field (400, under "childAges[1]"); a list that does not match the number of children is a request that does
 * not add up (422, under "childAges"). No children: the list may be absent or empty.
 */
class ChildAgesChallengeTest extends ApiTest {

    String family(String children, String ages) {
        return booking().replace("STANDARD", "FAMILY").replace("\"children\":0", "\"children\":" + children + (ages == null ? "" : ",\"childAges\":" + ages));
    }

    @Test
    void oneAgePerChild() throws Exception {
        book(family("2", "[4,11]")).andExpect(status().isCreated());
        book(family("0", null)).andExpect(status().isCreated());
        book(family("2", "[4]")).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.errors.childAges").value("give one age for each of the 2 children"));
        book(family("2", null)).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.errors.childAges").exists());
    }

    @Test
    void anAgeOutOfRangeIsABrokenField() throws Exception {
        book(family("2", "[4,18]")).andExpect(status().isBadRequest()).andExpect(jsonPath("$.errors['childAges[1]']").exists());
    }
}
