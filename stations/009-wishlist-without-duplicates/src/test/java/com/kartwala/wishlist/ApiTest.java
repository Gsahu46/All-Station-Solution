package com.kartwala.wishlist;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app through MockMvc, empty wishlists before each test. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    @Autowired
    MockMvc mvc;

    @Autowired
    Wishlists wishlists;

    @BeforeEach
    void emptyWishlists() {
        wishlists.clear();
    }

    ResultActions add(long wishlist, String sku) throws Exception {
        return mvc.perform(post("/wishlists/{id}/items", wishlist).contentType(MediaType.APPLICATION_JSON)
                .content("{\"sku\":\"" + sku + "\"}"));
    }
}
