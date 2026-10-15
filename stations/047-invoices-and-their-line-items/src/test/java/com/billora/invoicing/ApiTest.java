package com.billora.invoicing;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;

/**
 * Shared setup: the app on a real PostgreSQL, tables emptied before each test. The demo invoice is hosting (₹4,999)
 * and 6 support hours at ₹1,500: ₹13,999. The customer disputes 2 hours, so the corrected lines total ₹10,999.
 * Hibernate statistics are on, to count queries.
 */
@SpringBootTest(properties = "spring.jpa.properties.hibernate.generate_statistics=true")
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    static final String INVOICE = """
            {"customerName":"Kaveri Textiles Pvt Ltd","lines":[
              {"description":"Cloud hosting, March 2026","quantity":1,"unitPricePaise":499900},
              {"description":"Support hours","quantity":6,"unitPricePaise":150000}]}""";
    static final String CORRECTED = """
            {"lines":[
              {"description":"Cloud hosting, March 2026","quantity":1,"unitPricePaise":499900},
              {"description":"Support hours","quantity":4,"unitPricePaise":150000}]}""";

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void emptyTables() {
        jdbc.sql("TRUNCATE invoices, invoice_lines RESTART IDENTITY").update();
    }

    ResultActions create(String body) throws Exception {
        return mvc.perform(post("/invoices").contentType(MediaType.APPLICATION_JSON).content(body));
    }

    ResultActions replaceLines(long id, String body) throws Exception {
        return mvc.perform(put("/invoices/{id}/lines", id).contentType(MediaType.APPLICATION_JSON).content(body));
    }

    long lineRows(long invoice) {
        return jdbc.sql("SELECT count(*) FROM invoice_lines WHERE invoice_id = ?").param(invoice).query(Long.class).single();
    }

    /** What a finance report that sums the table would say. */
    long sumOfLineRows(long invoice) {
        return jdbc.sql("SELECT coalesce(sum(quantity * unit_price_paise), 0) FROM invoice_lines WHERE invoice_id = ?").param(invoice).query(Long.class).single();
    }
}
