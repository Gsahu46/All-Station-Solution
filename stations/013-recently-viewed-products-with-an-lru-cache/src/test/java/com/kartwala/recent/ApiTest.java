package com.kartwala.recent;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app through MockMvc, empty history before each test. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    @Autowired
    MockMvc mvc;

    @Autowired
    RecentlyViewed recentlyViewed;

    @BeforeEach
    void emptyHistory() {
        recentlyViewed.clear();
    }

    ResultActions view(long userId, long productId) throws Exception {
        return mvc.perform(post("/users/{id}/recently-viewed", userId)
                .contentType(MediaType.APPLICATION_JSON).content("{\"productId\":" + productId + "}"));
    }
}
