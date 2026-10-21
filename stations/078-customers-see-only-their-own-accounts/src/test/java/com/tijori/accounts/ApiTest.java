package com.tijori.accounts;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/** Shared setup: the whole app with its security on a real PostgreSQL holding the demo customers and accounts. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    /** Demo customers sign in as name@example.com with name-demo-pass. */
    ResultActions account(String customer, Object id) throws Exception {
        return mvc.perform(get("/accounts/{id}", id).with(httpBasic(customer + "@example.com", customer + "-demo-pass")));
    }

    ResultActions statement(String customer, Object id, String month) throws Exception {
        return mvc.perform(get("/accounts/{id}/statements", id).param("month", month).with(httpBasic(customer + "@example.com", customer + "-demo-pass")));
    }
}
