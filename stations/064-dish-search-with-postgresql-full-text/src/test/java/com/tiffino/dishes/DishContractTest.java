package com.tiffino.dishes;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.containsInAnyOrder;
import static org.hamcrest.Matchers.empty;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class DishContractTest extends ApiTest {

    @Test
    void paneerTikkaFindsEveryDishWithBothWordsNameMatchesFirst() throws Exception {
        mvc.perform(get("/dishes/search").param("q", "paneer tikka").param("city", "pune")).andExpect(status().isOk())
                .andExpect(jsonPath("$.q").value("paneer tikka")).andExpect(jsonPath("$.city").value("pune"))
                .andExpect(jsonPath("$.dishes", hasSize(4)))
                .andExpect(jsonPath("$.dishes[0:3].name", containsInAnyOrder("Tandoori Paneer Tikka Roll", "Paneer Tikka Masala", "Paneer Tikka")))
                .andExpect(jsonPath("$.dishes[3].name").value("Butter Chicken"))   // only its description mentions paneer tikka
                .andExpect(jsonPath("$.dishes[0].pricePaise").isNumber());
    }

    @Test
    void caseWordOrderAndPluralsDoNotMatter() throws Exception {
        mvc.perform(get("/dishes/search").param("q", "TIKKAS PANEER").param("city", "Pune")).andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes", hasSize(4)));
        mvc.perform(get("/dishes/search").param("q", "dosas").param("city", "pune")).andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes[*].name", containsInAnyOrder("Masala Dosa", "Mysore Masala Dosa")));
    }

    @Test
    void searchSyntaxPeopleAlreadyKnow() throws Exception {
        mvc.perform(get("/dishes/search").param("q", "\"masala dosa\" -mysore").param("city", "pune")).andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes[*].name", contains("Masala Dosa")));
        mvc.perform(get("/dishes/search").param("q", "dosa or coffee").param("city", "pune")).andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes", hasSize(3)));
    }

    @Test
    void oddCharactersAreSearchedNotParsed() throws Exception {
        mvc.perform(get("/dishes/search").param("q", "paneer & | ! ( :*").param("city", "pune")).andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes", hasSize(4)));
    }

    @Test
    void noMatchIsAnEmptyList() throws Exception {
        mvc.perform(get("/dishes/search").param("q", "the and of").param("city", "pune")).andExpect(status().isOk())   // only stop words
                .andExpect(jsonPath("$.dishes", empty()));
        mvc.perform(get("/dishes/search").param("q", "paneer tikka").param("city", "delhi")).andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes", empty()));
    }

    @Test
    void aTypoFindsNothingThatIsTheLimit() throws Exception {
        mvc.perform(get("/dishes/search").param("q", "panner").param("city", "pune")).andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes", empty()));
    }

    @Test
    void badParametersAre400() throws Exception {
        mvc.perform(get("/dishes/search").param("city", "pune")).andExpect(status().isBadRequest());
        mvc.perform(get("/dishes/search").param("q", "p").param("city", "pune")).andExpect(status().isBadRequest());
        mvc.perform(get("/dishes/search").param("q", "x".repeat(101)).param("city", "pune")).andExpect(status().isBadRequest());
        mvc.perform(get("/dishes/search").param("q", "paneer")).andExpect(status().isBadRequest());
        mvc.perform(get("/dishes/search").param("q", "paneer").param("city", "pune1")).andExpect(status().isBadRequest());
    }
}
