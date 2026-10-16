package com.kartwala.catalog;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class CatalogContractTest extends ApiTest {

    static final String SAREE = """
            {"sku": "t-saree-silk-red", "name": "Kanjeevaram Silk", "category": "sarees", "sellerId": 8, "pricePaise": 1250000,
             "attributes": {"fabric": "silk", "colour": "Red", "length_m": "6.3"}}""";

    @Test
    void aNewCategoryNeedsNoSchemaChange() throws Exception {
        create(SAREE).andExpect(status().isCreated())
                .andExpect(header().string("Location", matchesPattern("/catalog/products/[0-9a-f]{24}")))
                .andExpect(jsonPath("$.sku").value("T-SAREE-SILK-RED")).andExpect(jsonPath("$.attributes.fabric").value("silk"));
        mvc.perform(get("/catalog/products").param("category", "sarees").param("attr.fabric", "silk")).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].sku", contains("T-SAREE-SILK-RED")));
    }

    @Test
    void searchByCategoryAndAttributes() throws Exception {
        mvc.perform(get("/catalog/products").param("category", "phones").param("attr.ram", "8GB")).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].sku", contains("PH-NOVA-8-128", "PH-NOVA-8-256")));
        mvc.perform(get("/catalog/products").param("attr.size", "9").param("attr.material", "leather")).andExpect(status().isOk())
                .andExpect(jsonPath("$[*].sku", contains("SH-OXF-9-BRN")));
        mvc.perform(get("/catalog/products").param("category", "phones").param("attr.ram", "12GB")).andExpect(status().isOk())
                .andExpect(jsonPath("$", empty()));
    }

    @Test
    void aDuplicateSkuIs409() throws Exception {
        create(SAREE).andExpect(status().isCreated());
        create(SAREE).andExpect(status().isConflict()).andExpect(jsonPath("$.detail").value("SKU T-SAREE-SILK-RED already exists"));
    }

    @Test
    void malformedProductsAre400() throws Exception {
        create(SAREE.replace("1250000", "-5")).andExpect(status().isBadRequest());
        create(SAREE.replace("1250000", "12500.5")).andExpect(status().isBadRequest());
        create(SAREE.replace("\"fabric\"", "\"$where\"")).andExpect(status().isBadRequest());
        create(SAREE.replace("\"silk\"", "{\"$gt\": \"\"}")).andExpect(status().isBadRequest());   // an operator where a value belongs
    }

    @Test
    void queryOperatorsInParametersAreRefused() throws Exception {
        mvc.perform(get("/catalog/products").param("attr.$where", "1")).andExpect(status().isBadRequest());
        mvc.perform(get("/catalog/products").param("attr.attributes.ram", "8GB")).andExpect(status().isBadRequest());
        mvc.perform(get("/catalog/products").param("category", "{\"$ne\": null}")).andExpect(status().isBadRequest());
        mvc.perform(get("/catalog/products")).andExpect(status().isBadRequest());
    }
}
