package com.kartwala.wishlist;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: add, read, remove, and every way a request can be refused. */
class WishlistContractTest extends ApiTest {

    @Test
    void addingIs201WithTheWholeWishlist() throws Exception {
        add(7, "ph-12")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.wishlistId").value(7))
                .andExpect(jsonPath("$.count").value(1))
                .andExpect(jsonPath("$.items[0].sku").value("PH-12"))
                .andExpect(jsonPath("$.items[0].name").value("Samsung Galaxy M35 5G"))
                .andExpect(jsonPath("$.items[0].pricePaise").value(1699900));
    }

    @Test
    void itemsKeepTheOrderTheyWereAdded() throws Exception {
        add(7, "TV-55");
        add(7, "eb-141");
        add(7, "PH-12");
        add(7, "tv-55"); // already there: does not move to the end
        mvc.perform(get("/wishlists/7")).andExpect(jsonPath("$.items[*].sku", contains("TV-55", "EB-141", "PH-12")));
    }

    @Test
    void wishlistsAreSeparate() throws Exception {
        add(7, "PH-12");
        mvc.perform(get("/wishlists/8")).andExpect(jsonPath("$.count").value(0));
    }

    @Test
    void removingIs204InAnyLetterCaseAndAgainIs204() throws Exception {
        add(7, "PH-12");
        add(7, "TV-55");
        mvc.perform(delete("/wishlists/7/items/{sku}", "ph-12")).andExpect(status().isNoContent());
        mvc.perform(delete("/wishlists/7/items/{sku}", "PH-12")).andExpect(status().isNoContent());
        mvc.perform(get("/wishlists/7")).andExpect(jsonPath("$.items[*].sku", contains("TV-55")));
    }

    @Test
    void aMalformedSkuIs400WithoutEchoingIt() throws Exception {
        add(7, "<b>x</b>").andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Invalid SKU"))
                .andExpect(content().string(not(containsString("<b>"))));
        add(7, "   ").andExpect(status().isBadRequest());
        mvc.perform(post("/wishlists/7/items").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest()).andExpect(jsonPath("$.errors.sku").value("must not be null"));
    }

    @Test
    void aWellFormedSkuThatIsNotInTheCatalogIs422() throws Exception {
        add(7, "XX-99").andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Unknown product"));
    }

    @Test
    void anUnknownWishlistIs404() throws Exception {
        mvc.perform(get("/wishlists/999")).andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
        add(999, "PH-12").andExpect(status().isNotFound());
        mvc.perform(delete("/wishlists/999/items/PH-12")).andExpect(status().isNotFound());
    }
}
