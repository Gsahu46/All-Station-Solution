package com.basketo.stores;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.util.Locale;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: accept store ids in any letter case, on a server in any locale. */
class CaseInsensitiveIdChallengeTest extends ApiTest {

    private final Locale original = Locale.getDefault();

    @AfterEach
    void restoreLocale() {
        Locale.setDefault(original);
    }

    @Test
    void lowerCaseIdFindsTheStoreAndAnswersWithTheCanonicalId() throws Exception {
        mvc.perform(get("/stores/blr-kor-01/status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.storeId").value("BLR-KOR-01"));
    }

    @Test
    void aTurkishServerLocaleDoesNotBreakIdsContainingI() throws Exception {
        Locale.setDefault(Locale.forLanguageTag("tr-TR")); // "i".toUpperCase() is now a dotted capital İ
        mvc.perform(get("/stores/blr-ind-01/status"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.storeId").value("BLR-IND-01"));
    }

    @Test
    void stillA400WhenTheShapeIsWrong() throws Exception {
        mvc.perform(get("/stores/koramangala/status")).andExpect(status().isBadRequest());
    }
}
