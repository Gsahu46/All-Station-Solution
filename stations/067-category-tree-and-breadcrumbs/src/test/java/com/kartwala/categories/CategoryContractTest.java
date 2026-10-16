package com.kartwala.categories;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class CategoryContractTest extends ApiTest {

    @Test
    void theBreadcrumbRunsFromHomeToTheCategory() throws Exception {
        mvc.perform(get("/categories/4/breadcrumb")).andExpect(status().isOk())
                .andExpect(jsonPath("$.path").value("Home > Electronics > Phones > Android"))
                .andExpect(jsonPath("$.trail[*].slug", contains("home", "electronics", "phones", "android")));
        mvc.perform(get("/categories/1/breadcrumb")).andExpect(status().isOk()).andExpect(jsonPath("$.path").value("Home"));
        mvc.perform(get("/categories/112/breadcrumb")).andExpect(status().isOk()).andExpect(jsonPath("$.trail", hasSize(14)));
    }

    @Test
    void descendantsReadLikeAnIndentedMenu() throws Exception {
        mvc.perform(get("/categories/8/descendants")).andExpect(status().isOk())
                .andExpect(jsonPath("$.descendants[*].name", contains("Men", "Shoes", "Women", "Sarees", "Shoes")))
                .andExpect(jsonPath("$.descendants[*].depth", contains(1, 2, 1, 2, 2)))
                .andExpect(jsonPath("$.descendants[4].id").value(13)).andExpect(jsonPath("$.descendants[4].parentId").value(11));
        mvc.perform(get("/categories/1/descendants")).andExpect(status().isOk()).andExpect(jsonPath("$.descendants", hasSize(25)));
    }

    @Test
    void aLeafHasNoDescendants() throws Exception {
        mvc.perform(get("/categories/5/descendants")).andExpect(status().isOk()).andExpect(jsonPath("$.descendants", empty()));
    }

    @Test
    void anUnknownCategoryIs404AndANonNumberIs400() throws Exception {
        mvc.perform(get("/categories/999/breadcrumb")).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No category 999"));
        mvc.perform(get("/categories/999/descendants")).andExpect(status().isNotFound());
        mvc.perform(get("/categories/phones/breadcrumb")).andExpect(status().isBadRequest());
    }
}
