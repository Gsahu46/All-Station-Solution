package com.tiffino.addresses;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import java.util.Locale;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: PUT, PATCH, DELETE and GET on one named address, and every way a request can be refused. */
class AddressContractTest extends ApiTest {

    private final Locale original = Locale.getDefault();

    @AfterEach
    void restoreLocale() {
        Locale.setDefault(original);
    }

    @Test
    void aNewLabelIs201WithLocationAndCanBeRead() throws Exception {
        putAddress(42, "home", HOME)
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "/customers/42/addresses/home"))
                .andExpect(jsonPath("$.pincode").value("560038"));
        mvc.perform(get("/customers/42/addresses/home")).andExpect(status().isOk()).andExpect(content().json(HOME));
    }

    @Test
    void putReplacesTheWholeAddressSoLeftOutFieldsAreGone() throws Exception {
        putAddress(42, "home", HOME);
        putAddress(42, "home", """
                {"line1":"House 7, Defence Colony","city":"Bengaluru","pincode":"560038"}""")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.line2").isEmpty())
                .andExpect(jsonPath("$.landmark").isEmpty());
    }

    @Test
    void labelsIgnoreLetterCaseEvenOnATurkishServer() throws Exception {
        Locale.setDefault(Locale.forLanguageTag("tr-TR")); // "OFFICE".toLowerCase() would contain a dotless ı
        putAddress(42, "OFFICE", HOME).andExpect(header().string("Location", "/customers/42/addresses/office"));
        mvc.perform(get("/customers/42/addresses/office")).andExpect(status().isOk());
    }

    @Test
    void anInvalidLabelOrBodyIs400() throws Exception {
        putAddress(42, "home!", HOME).andExpect(status().isBadRequest()).andExpect(jsonPath("$.title").value("Invalid label"));
        putAddress(42, "home", HOME.replace("560038", "060038"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.pincode").value("must be a 6-digit PIN code"));
        putAddress(42, "home", "{\"line1\":\"\",\"city\":\"Pune\",\"pincode\":\"411001\"}")
                .andExpect(jsonPath("$.errors.line1").value("must not be blank"));
    }

    @Test
    void patchChangesOnlyTheFieldsSent() throws Exception {
        putAddress(42, "home", HOME);
        patchAddress(42, "home", "{\"landmark\":\"Next to Indiranagar metro\"}")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.landmark").value("Next to Indiranagar metro"))
                .andExpect(jsonPath("$.line1").value("Flat 402, Lotus Residency"))
                .andExpect(jsonPath("$.line2").value("14th Cross, Indiranagar"));
    }

    @Test
    void patchWithNullRemovesAnOptionalField() throws Exception {
        putAddress(42, "home", HOME);
        patchAddress(42, "home", "{\"line2\":null}").andExpect(jsonPath("$.line2").isEmpty())
                .andExpect(jsonPath("$.landmark").value("Opposite Cafe Coffee Day"));
    }

    @Test
    void patchCannotRemoveARequiredFieldAndChangesNothing() throws Exception {
        putAddress(42, "home", HOME);
        patchAddress(42, "home", "{\"city\":null,\"landmark\":\"x\"}")
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.city").value("must not be blank"));
        mvc.perform(get("/customers/42/addresses/home")).andExpect(content().json(HOME));
    }

    @Test
    void patchWithAnUnknownFieldOrANonObjectIs400WithoutEchoingIt() throws Exception {
        putAddress(42, "home", HOME);
        patchAddress(42, "home", "{\"<b>owner</b>\":\"ravi\"}")
                .andExpect(status().isBadRequest())
                .andExpect(content().string(not(containsString("<b>"))));
        patchAddress(42, "home", "[1,2]").andExpect(status().isBadRequest());
        patchAddress(42, "home", "{\"pincode\":560038}").andExpect(status().isBadRequest());
    }

    @Test
    void patchingAnAddressThatDoesNotExistIs404() throws Exception {
        patchAddress(42, "work", "{\"landmark\":\"x\"}").andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
    }

    @Test
    void deleteIs204AndTheAddressIsGone() throws Exception {
        putAddress(42, "home", HOME);
        deleteAddress(42, "home").andExpect(status().isNoContent()).andExpect(content().string(""));
        mvc.perform(get("/customers/42/addresses/home")).andExpect(status().isNotFound());
    }

    @Test
    void postIs405AndTheAllowHeaderListsWhatWorks() throws Exception {
        mvc.perform(post("/customers/42/addresses/home").contentType(MediaType.APPLICATION_JSON).content(HOME))
                .andExpect(status().isMethodNotAllowed())
                .andExpect(header().string("Allow", containsString("PUT")))
                .andExpect(header().string("Allow", containsString("PATCH")))
                .andExpect(header().string("Allow", containsString("DELETE")))
                .andExpect(header().string("Allow", containsString("GET")))
                .andExpect(header().string("Allow", not(containsString("POST"))));
    }

    @Test
    void anUnknownCustomerIs404() throws Exception {
        putAddress(999, "home", HOME).andExpect(status().isNotFound()).andExpect(jsonPath("$.title").value("Customer not found"));
    }

    @Test
    void theEleventhLabelIs409ButReplacingAnExistingOneStillWorks() throws Exception {
        for (int i = 1; i <= 10; i++) {
            putAddress(43, "place-" + i, HOME).andExpect(status().isCreated());
        }
        putAddress(43, "place-11", HOME).andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Address book full"));
        putAddress(43, "place-3", HOME).andExpect(status().isOk());
    }
}
