package com.kartwala.wishlist;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * The same phone arrives as "ph-12" (search page), "PH-12" (product page) and " PH-12 " (an old app).
 */
@Import(EqualsWithoutHashCodeTrapTest.OldWishlistController.class)
class EqualsWithoutHashCodeTrapTest extends ApiTest {

    /** The "before" key: equals ignores case and spaces, but hashCode was never overridden. */
    static final class OldSku {
        final String value;

        OldSku(String value) {
            this.value = value;
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof OldSku other && value.strip().equalsIgnoreCase(other.value.strip());
        }
        // no hashCode(): Object's version gives each object its own number, so HashSet never even calls equals
    }

    /** A key someone can change after it went into the set. */
    static final class MutableSku {
        String value;

        MutableSku(String value) {
            this.value = value;
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof MutableSku other && value.equals(other.value);
        }

        @Override
        public int hashCode() {
            return value.hashCode();
        }
    }

    @RestController
    static class OldWishlistController {
        private final Set<OldSku> items = new HashSet<>();

        @PostMapping("/old/wishlists/7/items")
        synchronized void add(@RequestBody Map<String, String> body) {
            items.add(new OldSku(body.get("sku")));
        }

        @GetMapping("/old/wishlists/7")
        synchronized Object get() {
            return items.stream().map(s -> s.value).toList();
        }
    }

    @Test
    void equalsWithoutHashCodeLetsTheSamePhoneInThreeTimes() throws Exception {
        for (String sku : new String[]{"ph-12", "PH-12", " PH-12 "}) {
            mvc.perform(post("/old/wishlists/7/items").contentType("application/json").content("{\"sku\":\"" + sku + "\"}"))
                    .andExpect(status().isOk());
        }
        mvc.perform(get("/old/wishlists/7")).andExpect(jsonPath("$", hasSize(3))); // the bug from the support ticket
    }

    @Test
    void aKeyChangedAfterInsertionIsLostInsideTheSet() {
        Set<MutableSku> set = new HashSet<>();
        MutableSku phone = new MutableSku("PH-12");
        set.add(phone);
        phone.value = "PH-13";                                    // someone "fixes" the SKU in place
        assertThat(set).hasSize(1);
        assertThat(set.contains(new MutableSku("PH-13"))).isFalse(); // stored in PH-12's bucket, looked up in PH-13's
        assertThat(set.remove(phone)).isFalse();                  // and it cannot even be removed
    }

    @Test
    void theRealWishlistKeepsOnePhone() throws Exception {
        add(7, "ph-12").andExpect(status().isCreated());
        add(7, "PH-12").andExpect(status().isOk());
        add(7, " PH-12 ").andExpect(status().isOk());
        mvc.perform(get("/wishlists/7")).andExpect(jsonPath("$.count").value(1)).andExpect(jsonPath("$.items[0].sku").value("PH-12"));
    }
}
