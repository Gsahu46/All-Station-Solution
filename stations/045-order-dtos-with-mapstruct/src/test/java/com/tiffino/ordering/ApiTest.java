package com.tiffino.ordering;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import tools.jackson.databind.json.JsonMapper;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the app on a real PostgreSQL, no orders before each test. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    static final String ORDER = """
            {"customerName":"Asha Verma","phone":"9876543210",
             "address":{"line":"Flat 4B, Lotus Residency, Baner Road","city":"Pune","pincode":"411045"},
             "deliveryInstructions":"Ring twice, baby sleeping",
             "lines":[{"item":"Paneer thali","quantity":2,"unitPricePaise":24900},{"item":"Masala chaas","quantity":1,"unitPricePaise":4900}]}""";

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    OrderMapper mapper;
    @Autowired
    JsonMapper json;

    /** A request as the API would receive it, read by the app's own JSON mapper (no Java validation runs). */
    OrderDtos.CreateOrderRequest request(String body) {
        return json.readValue(body, OrderDtos.CreateOrderRequest.class);
    }

    @BeforeEach
    void noOrders() {
        jdbc.sql("TRUNCATE order_lines, orders RESTART IDENTITY").update();
    }

    ResultActions place(String json) throws Exception {
        return mvc.perform(post("/orders").contentType(MediaType.APPLICATION_JSON).content(json));
    }
}
