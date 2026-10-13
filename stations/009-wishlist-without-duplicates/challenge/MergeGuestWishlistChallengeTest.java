package com.kartwala.wishlist;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: a guest's wishlist is merged into the customer's when they sign in. No duplicates, all or nothing. */
class MergeGuestWishlistChallengeTest extends ApiTest {

    ResultActions merge(String skusJson) throws Exception {
        return mvc.perform(post("/wishlists/7/merge").contentType(MediaType.APPLICATION_JSON).content("{\"skus\":" + skusJson + "}"));
    }

    @Test
    void mergeKeepsExistingItemsFirstAndAddsOnlyNewOnes() throws Exception {
        add(7, "PH-12");
        merge("[\"ph-12\", \"TV-55\", \" tv-55 \", \"eb-141\"]")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items[*].sku", contains("PH-12", "TV-55", "EB-141")));
    }

    @Test
    void oneBadSkuMeansNothingIsMerged() throws Exception {
        add(7, "PH-12");
        merge("[\"TV-55\", \"bad sku\"]").andExpect(status().isBadRequest());
        merge("[\"TV-55\", \"XX-99\"]").andExpect(status().isUnprocessableContent());
        mvc.perform(get("/wishlists/7")).andExpect(jsonPath("$.items[*].sku", contains("PH-12")));
    }

    @Test
    void mergingTheSameListTwiceChangesNothingTheSecondTime() throws Exception {
        merge("[\"TV-55\", \"CK-5L\"]");
        merge("[\"TV-55\", \"CK-5L\"]").andExpect(jsonPath("$.count").value(2));
    }
}
