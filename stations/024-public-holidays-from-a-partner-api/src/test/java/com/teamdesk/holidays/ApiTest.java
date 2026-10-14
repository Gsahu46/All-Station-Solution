package com.teamdesk.holidays;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/**
 * Shared setup: the whole app through MockMvc, calling the stub provider instead of the demo one, with a short read
 * timeout so the slow case takes milliseconds, not seconds.
 */
@SpringBootTest(properties = {"teamdesk.demo-provider.enabled=false", "teamdesk.holidays.read-timeout=400ms"})
@AutoConfigureMockMvc
abstract class ApiTest {

    static final StubProvider STUB = StubProvider.start();

    @DynamicPropertySource
    static void provider(DynamicPropertyRegistry registry) {
        registry.add("teamdesk.holidays.base-url", STUB::baseUrl);
    }

    @Autowired
    MockMvc mvc;

    @BeforeEach
    void providerBehavesNormally() {
        STUB.behaviour = StubProvider.Behaviour.NORMAL;
    }

    ResultActions holidays(String year, String state) throws Exception {
        return mvc.perform(get("/holidays").param("year", year).param("state", state));
    }
}
