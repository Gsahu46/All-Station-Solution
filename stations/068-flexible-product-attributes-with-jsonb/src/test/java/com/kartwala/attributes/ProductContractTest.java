package com.kartwala.attributes;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.hamcrest.Matchers.startsWith;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class ProductContractTest extends ApiTest {

    static final String PHONE = """
            {"sku": "t-pixel-12-256", "name": "Pixel Pro", "category": "phones", "sellerId": 7, "pricePaise": 5999900,
             "attributes": {"ram": "12GB", "storage": "256GB", "colour": "Obsidian"}}""";

    @Test
    void aPhoneWithItsOwnAttributesIsCreated() throws Exception {
        create(PHONE).andExpect(status().isCreated()).andExpect(header().string("Location", startsWith("/products/")))
                .andExpect(jsonPath("$.sku").value("T-PIXEL-12-256")).andExpect(jsonPath("$.attributes.ram").value("12GB"))
                .andExpect(jsonPath("$.attributes.colour").value("Obsidian")).andExpect(jsonPath("$.pricePaise").value(5999900));
    }

    @Test
    void attributesAreCheckedAgainstTheCategorysRules() throws Exception {
        create("""
                {"sku": "t-bad-shoe", "name": "Odd Shoe", "category": "shoes", "sellerId": 8, "pricePaise": 99900,
                 "attributes": {"size": "13", "ram": "8GB"}}""").andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.detail").value("These attributes do not fit a shoes product"))
                .andExpect(jsonPath("$.attributes.size").value("must be one of [6, 7, 8, 9, 10, 11]"))
                .andExpect(jsonPath("$.attributes.ram").value("not an attribute of this category; known: [colour, material, size]"))
                .andExpect(jsonPath("$.attributes.colour").value("is required"));
    }

    @Test
    void unknownCategorySellerOrADuplicateSku() throws Exception {
        create(PHONE.replace("\"phones\"", "\"laptops\"")).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("No category laptops"));
        create(PHONE.replace("\"sellerId\": 7", "\"sellerId\": 99")).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("No seller 99"));
        create(PHONE).andExpect(status().isCreated());
        create(PHONE).andExpect(status().isConflict());
    }

    @Test
    void malformedBodiesAre400() throws Exception {
        create(PHONE.replace("5999900", "5999900.5")).andExpect(status().isBadRequest());
        create(PHONE.replace("5999900", "0")).andExpect(status().isBadRequest());
        create(PHONE.replace("\"Obsidian\"", "\"\"")).andExpect(status().isBadRequest());
        create(PHONE.replace("\"colour\"", "\"Colour!\"")).andExpect(status().isBadRequest());
        create(PHONE.replace("\"attributes\": {\"ram\": \"12GB\", \"storage\": \"256GB\", \"colour\": \"Obsidian\"}", "\"attributes\": [\"12GB\"]")).andExpect(status().isBadRequest());
    }

    @Test
    void searchByAnyMixOfAttributes() throws Exception {
        mvc.perform(get("/products").param("category", "phones").param("attr.ram", "8GB").param("attr.storage", "256GB")).andExpect(status().isOk())
                .andExpect(jsonPath("$[0].sku").value("PH-NOVA-8-256")).andExpect(jsonPath("$[0].attributes.colour").value("Blue"));
        mvc.perform(get("/products").param("attr.size", "9").param("attr.material", "leather")).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].sku", contains("SH-OXF-9-BRN")));
        mvc.perform(get("/products").param("category", "phones").param("attr.ram", "12GB")).andExpect(status().isOk())
                .andExpect(jsonPath("$", empty()));
    }

    @Test
    void searchingForSomethingNoCategoryHasIs400() throws Exception {
        mvc.perform(get("/products").param("category", "shoes").param("attr.ram", "8GB")).andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("No attribute ram for shoes"));
        mvc.perform(get("/products").param("attr.wheels", "4")).andExpect(status().isBadRequest());
        mvc.perform(get("/products").param("category", "laptops").param("attr.ram", "8GB")).andExpect(status().isBadRequest());
        mvc.perform(get("/products").param("ram", "8GB")).andExpect(status().isBadRequest());
        mvc.perform(get("/products")).andExpect(status().isBadRequest());
    }
}
