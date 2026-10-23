package com.dakroute.shipments;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.util.List;
import java.util.stream.Collectors;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app on a real PostgreSQL, no shipments before each test, and a builder for items. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void noShipments() {
        jdbc.sql("TRUNCATE shipments RESTART IDENTITY").update();
    }

    /** A good shipment to Delhi; tests change one field with replace(). */
    static String item(String ref) {
        return """
                {"ref":"%s","fromPincode":"560001","weightGrams":1200,
                 "to":{"name":"Meera Iyer","line1":"14 Lodhi Road","city":"New Delhi","pincode":"110003","phone":"9810000001"}}""".formatted(ref);
    }

    ResultActions bulk(List<String> items) throws Exception {
        return bulkBody("{\"shipments\":[" + items.stream().collect(Collectors.joining(",")) + "]}");
    }

    ResultActions bulkBody(String json) throws Exception {
        return mvc.perform(post("/shipments/bulk").contentType(MediaType.APPLICATION_JSON).content(json));
    }

    long count() {
        return jdbc.sql("SELECT count(*) FROM shipments").query(Long.class).single();
    }
}
