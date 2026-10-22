package com.streamo.config;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/** Shared setup: the whole app, the demo config as published at start before each test. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    AppConfigs configs;

    @BeforeEach
    void demoConfig() {
        configs.reset();
    }

    static MockHttpServletRequestBuilder config(String platform, String version) {
        return get("/app-config").param("platform", platform).param("version", version);
    }

    MockHttpServletResponse ask(String platform, String version, String ifNoneMatch) throws Exception {
        MockHttpServletRequestBuilder r = config(platform, version);
        if (ifNoneMatch != null) {
            r.header("If-None-Match", ifNoneMatch);
        }
        return mvc.perform(r).andReturn().getResponse();
    }
}
