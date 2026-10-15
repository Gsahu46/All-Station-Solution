package com.mediqo.pharmacy;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import javax.sql.DataSource;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/** Shared setup: the whole app, a real PostgreSQL with the demo catalogue from the migrations. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    DataSource dataSource;

    ResultActions search(String name) throws Exception {
        return mvc.perform(name == null ? get("/medicines") : get("/medicines").param("name", name));
    }
}
