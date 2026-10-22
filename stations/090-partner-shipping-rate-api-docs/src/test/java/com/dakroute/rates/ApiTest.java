package com.dakroute.rates;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app, request helpers, and the generated OpenAPI description. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    static final JsonMapper JSON = JsonMapper.builder().build();

    @Autowired
    MockMvc mvc;

    ResultActions quote(String json) throws Exception {
        return mvc.perform(post("/rate-quotes").contentType(MediaType.APPLICATION_JSON).content(json));
    }

    MockHttpServletResponse quoteResponse(String json) throws Exception {
        return quote(json).andReturn().getResponse();
    }

    JsonNode spec() throws Exception {
        return JSON.readTree(mvc.perform(get("/v3/api-docs")).andReturn().getResponse().getContentAsString());
    }
}
