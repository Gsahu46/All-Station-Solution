package com.paysetu.webhooks;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.bean.override.convention.TestBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.time.Clock;
import java.time.Instant;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Shared setup: the whole app on a real PostgreSQL, the scheduler off (tests run dispatcher rounds themselves) and a
 * clock the test moves. Attempts time out after 500 ms here instead of 5 s.
 */
@SpringBootTest(properties = {"paysetu.webhooks.dispatcher.enabled=false", "paysetu.webhooks.timeout=500ms"})
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    static final Instant T0 = Instant.parse("2026-10-23T10:00:00Z");
    static final TestClock CLOCK = new TestClock(T0);
    static final JsonMapper JSON = JsonMapper.builder().build();

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    Dispatcher dispatcher;

    @TestBean
    Clock clock;

    static Clock clock() {
        return CLOCK;
    }

    @BeforeEach
    void emptyTablesAndT0() {
        jdbc.sql("TRUNCATE delivery_attempts, deliveries, events, webhook_endpoints RESTART IDENTITY").update();
        CLOCK.set(T0);
    }

    static String password(String user) {
        return user + "-demo-pass";
    }

    ResultActions registerEndpoint(String user, long merchantId, String url) throws Exception {
        return mvc.perform(post("/merchants/{id}/webhook-endpoints", merchantId).with(httpBasic(user, password(user)))
                .contentType(MediaType.APPLICATION_JSON).content(JSON.writeValueAsString(java.util.Map.of("url", url))));
    }

    /** Registers the URL and returns the signing secret. */
    String secretFor(String user, long merchantId, String url) throws Exception {
        return json(registerEndpoint(user, merchantId, url).andExpect(status().isCreated())).get("secret").asString();
    }

    ResultActions testEvent(String user, long merchantId, String paymentRef, long amountPaise) throws Exception {
        return mvc.perform(post("/merchants/{id}/test-events", merchantId).with(httpBasic(user, password(user)))
                .contentType(MediaType.APPLICATION_JSON).content("{\"paymentRef\":" + JSON.writeValueAsString(paymentRef) + ",\"amountPaise\":" + amountPaise + "}"));
    }

    ResultActions deliveries(String user, String query) throws Exception {
        return mvc.perform(get("/webhook-deliveries" + query).with(httpBasic(user, password(user))));
    }

    static JsonNode json(ResultActions result) throws Exception {
        return JSON.readTree(result.andReturn().getResponse().getContentAsString());
    }

    /** The one delivery's log, as the merchant reads it. */
    JsonNode onlyDelivery(String user) throws Exception {
        JsonNode list = json(deliveries(user, "").andExpect(status().isOk()));
        return json(mvc.perform(get("/webhook-deliveries/{id}", list.get(0).get("id").asLong()).with(httpBasic(user, password(user)))));
    }
}
