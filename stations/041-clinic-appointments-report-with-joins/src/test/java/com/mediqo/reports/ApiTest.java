package com.mediqo.reports;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Shared setup: the app on a real PostgreSQL with the demo week from the migrations (5 to 11 October 2026).
 * Dr Mehta: 3 appointments that count (2 completed, 1 no-show), 3 follow-ups, plus 1 cancelled. Dr Iyer: 2.
 * Dr Rao: 1 this week, 1 next. Dr Khan: none. Dr Das: retired.
 */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    static final String FROM = "2026-10-05";
    static final String TO = "2026-10-11";

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    DoctorLoadReport report;
}
