package com.kartwala.search;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: what the search box can rely on as the customer types. */
class SuggestionContractTest extends ApiTest {

    @Test
    void prefixReturnsTheMostPopularMatchesWithIds() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "sam").param("limit", "3"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.prefix").value("sam"))
                .andExpect(jsonPath("$.suggestions", hasSize(3)))
                .andExpect(jsonPath("$.suggestions[0].productId").value(1))
                .andExpect(jsonPath("$.suggestions[*].name", contains(
                        "Samsung Galaxy M35 5G", "Samsung Galaxy S24", "Sambar Masala 100g")));
    }

    @Test
    void anyWordOfTheNameCanStartTheMatch() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "galaxy"))
                .andExpect(jsonPath("$.suggestions[*].name", contains(
                        "Samsung Galaxy M35 5G", "Samsung Galaxy S24", "Galaxy Chocolate Bar")));
    }

    @Test
    void letterCaseAndExtraSpacesDoNotMatter() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "  SAMSUNG    galaxy  s"))
                .andExpect(jsonPath("$.prefix").value("samsung galaxy s"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("Samsung Galaxy S24")));
    }

    @Test
    void theNameKeepsItsOriginalSpelling() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "boat"))
                .andExpect(jsonPath("$.suggestions[*].name", contains("boAt Airdopes 141", "boAt Rockerz 450")));
    }

    @Test
    void textInTheMiddleOfAWordIsNotAMatch() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "msung"))   // inside "Samsung"
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.suggestions", hasSize(0)));
    }

    @Test
    void noMatchIsAnEmptyListNotAnError() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "xyz"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.suggestions", hasSize(0)));
    }

    @Test
    void defaultLimitIsFive() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "sa"))
                .andExpect(jsonPath("$.suggestions", hasSize(5)));
    }

    @Test
    void missingPrefixIs400() throws Exception {
        mvc.perform(get("/suggestions"))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentType("application/problem+json"));
    }

    @Test
    void oneLetterAfterTrimmingIs400() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "  s   "))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentType("application/problem+json"))
                .andExpect(jsonPath("$.title").value("Invalid prefix"));
    }

    @Test
    void aPrefixLongerThan40CharactersIs400() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "a".repeat(41)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.title").value("Invalid prefix"));
    }

    @Test
    void aHugePrefixIsRejectedBeforeAnyWork() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "a".repeat(5000)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.prefix").value("size must be between 0 and 200"));
    }

    @Test
    void limitOutsideOneToTenIs400() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "sam").param("limit", "11"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.limit").value("must be less than or equal to 10"));
        mvc.perform(get("/suggestions").param("prefix", "sam").param("limit", "0"))
                .andExpect(status().isBadRequest());
    }
}
