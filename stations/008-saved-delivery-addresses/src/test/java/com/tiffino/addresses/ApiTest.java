package com.tiffino.addresses;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;

/** Shared setup: the whole app through MockMvc, empty address books before each test. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    static final String HOME = """
            {"line1":"Flat 402, Lotus Residency","line2":"14th Cross, Indiranagar","landmark":"Opposite Cafe Coffee Day","city":"Bengaluru","pincode":"560038"}
            """;

    @Autowired
    MockMvc mvc;

    @Autowired
    AddressBook book;

    @BeforeEach
    void emptyBooks() {
        book.clear();
    }

    ResultActions putAddress(long customer, String label, String json) throws Exception {
        return mvc.perform(put("/customers/{c}/addresses/{l}", customer, label).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    ResultActions patchAddress(long customer, String label, String json) throws Exception {
        return mvc.perform(patch("/customers/{c}/addresses/{l}", customer, label)
                .contentType("application/merge-patch+json").content(json));
    }

    ResultActions deleteAddress(long customer, String label) throws Exception {
        return mvc.perform(delete("/customers/{c}/addresses/{l}", customer, label));
    }
}
