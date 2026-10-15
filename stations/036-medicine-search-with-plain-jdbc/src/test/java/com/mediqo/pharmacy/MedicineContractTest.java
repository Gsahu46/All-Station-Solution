package com.mediqo.pharmacy;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.empty;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract against the demo catalogue. */
class MedicineContractTest extends ApiTest {

    @Test
    void aPartOfTheNameInAnyCaseFindsEveryForm() throws Exception {
        search("PARA").andExpect(status().isOk())
                .andExpect(jsonPath("$.query").value("PARA"))
                .andExpect(jsonPath("$.results[*].strength", contains("125 mg/5 ml", "500 mg", "650 mg")))
                .andExpect(jsonPath("$.results[0].form").value("SYRUP"))
                .andExpect(jsonPath("$.results[1].pricePaise").value(2000))
                .andExpect(jsonPath("$.results[1].prescriptionRequired").value(false));
        search("cillin").andExpect(jsonPath("$.results[0].name").value("Amoxicillin"))
                .andExpect(jsonPath("$.results[0].prescriptionRequired").value(true));
    }

    @Test
    void anApostropheIsJustACharacter() throws Exception {
        search("john's").andExpect(jsonPath("$.results[0].name").value("St. John's Wort"));
    }

    @Test
    void noMatchIsAnEmptyListNotAnError() throws Exception {
        search("aspirin").andExpect(status().isOk()).andExpect(jsonPath("$.results", empty()));
        search(ConcatenatedSqlTrapTest.ALWAYS_TRUE).andExpect(status().isOk()).andExpect(jsonPath("$.results", empty()));
    }

    @Test
    void wildcardsAreLiteral() throws Exception {
        search("%%").andExpect(jsonPath("$.results", empty()));   // as a wildcard, "%%" would match every medicine
        search("a_").andExpect(jsonPath("$.results", empty()));   // as a wildcard, "_" would match any letter after an "a"
    }

    @Test
    void aMissingTooShortOrTooLongNameIs400() throws Exception {
        search(null).andExpect(status().isBadRequest()).andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
        search("p").andExpect(status().isBadRequest());
        search("   ").andExpect(status().isBadRequest());
        search("a".repeat(51)).andExpect(status().isBadRequest());
    }
}
