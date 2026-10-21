package com.tijori.accounts;

import org.junit.jupiter.api.Test;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /accounts/{id}/statements.csv?month=2026-09 as a CSV download, with the same rules as the JSON
 * statement (404 for others' accounts, 403 for balance-only). Amounts in rupees from paise, two decimals, no
 * thousands separator; descriptions with a comma are quoted.
 */
class StatementCsvChallengeTest extends ApiTest {

    @Test
    void aMonthAsCsv() throws Exception {
        mvc.perform(get("/accounts/1001/statements.csv").param("month", "2026-09").with(httpBasic("zoya@example.com", "zoya-demo-pass")))
                .andExpect(status().isOk()).andExpect(header().string("Content-Type", "text/csv;charset=UTF-8"))
                .andExpect(header().string("Content-Disposition", "attachment; filename=\"tijori-1001-2026-09.csv\""))
                .andExpect(content().string("""
                        date,description,amount
                        2026-09-01,"Salary, Acme Analytics",95000.00
                        2026-09-05,"Rent, September",-32000.00
                        2026-09-18,UPI to Dev Patel,-1500.00
                        """));
    }

    @Test
    void theSameRulesAsTheJsonStatement() throws Exception {
        mvc.perform(get("/accounts/1002/statements.csv").param("month", "2026-09").with(httpBasic("zoya@example.com", "zoya-demo-pass"))).andExpect(status().isNotFound());
        mvc.perform(get("/accounts/1004/statements.csv").param("month", "2026-09").with(httpBasic("ravi@example.com", "ravi-demo-pass"))).andExpect(status().isForbidden());
    }
}
