package com.tiffino.menu;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.util.Locale;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: a q parameter that finds dishes by part of their name, in any letter case. */
class NameSearchChallengeTest extends ApiTest {

    private final Locale original = Locale.getDefault();

    @AfterEach
    void restoreLocale() {
        Locale.setDefault(original);
    }

    @Test
    void findsDishesContainingTheWordInAnyCase() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("q", "RICE").param("sort", "price_asc"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.dishes[*].name", contains("Curd Rice", "Lemon Rice")));
    }

    @Test
    void surroundingSpacesAreIgnoredAndOtherFiltersStillApply() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("q", "  masala ").param("veg", "true"))
                .andExpect(jsonPath("$.dishes[*].name", contains("Masala Dosa", "Paneer Butter Masala")));
    }

    @Test
    void aTurkishServerLocaleStillFindsIdli() throws Exception {
        Locale.setDefault(Locale.forLanguageTag("tr-TR")); // "IDLI".toLowerCase() would give "ıdlı"
        mvc.perform(get("/restaurants/101/menu").param("q", "IDLI"))
                .andExpect(jsonPath("$.dishes[*].name", contains("Idli Sambar")));
    }

    @Test
    void aSearchLongerThan40CharactersIs400() throws Exception {
        mvc.perform(get("/restaurants/101/menu").param("q", "x".repeat(41)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.q").exists());
    }
}
