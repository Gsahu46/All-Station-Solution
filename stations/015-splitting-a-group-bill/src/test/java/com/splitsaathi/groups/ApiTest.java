package com.splitsaathi.groups;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app through MockMvc, no expenses at the start of each test. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    @Autowired
    MockMvc mvc;

    @Autowired
    Groups groups;

    @BeforeEach
    void noExpenses() {
        groups.clear();
    }

    ResultActions expense(long group, String json) throws Exception {
        return mvc.perform(post("/groups/{id}/expenses", group).contentType(MediaType.APPLICATION_JSON).content(json));
    }
}
