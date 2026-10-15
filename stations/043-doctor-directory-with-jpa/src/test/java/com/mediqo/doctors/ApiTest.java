package com.mediqo.doctors;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Shared setup: the app on a real PostgreSQL with the demo directory. Cardiology: Dr Asha Mehta and Dr Fatima Ali
 * (Pune), Dr Kabir Khan (Bengaluru). Six doctors, two clinics. Hibernate statistics are on, to count queries.
 */
@SpringBootTest(properties = "spring.jpa.properties.hibernate.generate_statistics=true")
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    DoctorRepository doctors;
}
