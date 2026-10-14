package com.tijori.statementimport;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app through MockMvc, and a generator for long statements. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    static final String HEADER = "date,description,debit,credit,balance\n";

    @Autowired
    MockMvc mvc;

    ResultActions parse(String csv) throws Exception {
        return mvc.perform(post("/statements/parse").contentType("text/csv").content(csv));
    }

    /** A statement of n good lines (file lines 2 to n + 1), each a Rs 10 debit from Rs 2,00,000, with one line replaced if asked. */
    static String statement(int n, int badFileLine, String badLine) {
        StringBuilder csv = new StringBuilder(HEADER);
        for (int fileLine = 2; fileLine <= n + 1; fileLine++) {
            long balanceRupees = 200_000 - 10L * (fileLine - 1);
            csv.append(fileLine == badFileLine ? badLine : "01/04/2026,UPI to grocer,10.00,," + balanceRupees + ".00").append('\n');
        }
        return csv.toString();
    }
}
