package com.ghoomo.bookings;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: a company may add an optional "gstin" for its invoice. Write a field-level ConstraintValidator: 15
 * characters (2-digit state code, 10-character PAN, entity code, "Z", check character) and the published check
 * character method. Lower case is accepted; the booking shows it upper case. A wrong one is 400. A format check only:
 * it does not prove the GSTIN is registered.
 */
class GstinChallengeTest extends ApiTest {

    String withGstin(String gstin) {
        return booking().replace("\"guestName\"", "\"gstin\":\"" + gstin + "\",\"guestName\"");
    }

    @Test
    void aWellFormedGstinIsKeptUpperCase() throws Exception {
        book(withGstin("27aapfu0939f1zv")).andExpect(status().isCreated()).andExpect(jsonPath("$.gstin").value("27AAPFU0939F1ZV"));
        book(booking()).andExpect(status().isCreated()).andExpect(jsonPath("$.gstin").doesNotExist());
    }

    @Test
    void aWrongCheckCharacterOrShapeIs400() throws Exception {
        book(withGstin("27AAPFU0939F1ZW")).andExpect(status().isBadRequest()).andExpect(jsonPath("$.errors.gstin").exists());
        book(withGstin("27AAPFU0939F1V")).andExpect(status().isBadRequest());
        book(withGstin("2AAAPFU0939F1ZV")).andExpect(status().isBadRequest());
    }
}
