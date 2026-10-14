package com.tijori.statementimport;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: a clean statement, a statement with several bad lines, and files that cannot be read at all. */
class StatementContractTest extends ApiTest {

    @Test
    void aCleanStatementIsComplete() throws Exception {
        parse(HEADER + """
                01/04/2026,"UPI/GROCER, BLR","1,234.50",,98765.50
                2026-04-02,Salary,,"1,20,000",218765.50
                03-04-2026,"ATM \"\"Koramangala\"\"\",500,,218265.50
                """)
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("COMPLETE"))
                .andExpect(jsonPath("$.errorCount").value(0))
                .andExpect(jsonPath("$.transactions[0].line").value(2))
                .andExpect(jsonPath("$.transactions[0].date").value("2026-04-01"))
                .andExpect(jsonPath("$.transactions[0].description").value("UPI/GROCER, BLR"))
                .andExpect(jsonPath("$.transactions[0].debitPaise").value(123450))
                .andExpect(jsonPath("$.transactions[1].creditPaise").value(12000000))
                .andExpect(jsonPath("$.transactions[2].description").value("ATM \"Koramangala\""))
                .andExpect(jsonPath("$.transactions[2].date").value("2026-04-03"));
    }

    @Test
    void everyBadLineIsListedWithItsLineNumber() throws Exception {
        parse(HEADER + """
                01/04/2026,Rent,25000,,75000
                31/02/2026,Impossible date,10,,74990
                02/04/2026,Two amounts,10,10,74990
                02/04/2026,Bad amount,12.345,,74990
                02/04/2026,"Unclosed quote,10,,74990
                02/04/2026,Too few fields,10
                02/04/2026,,10,,74990
                """)
                .andExpect(jsonPath("$.status").value("PARTIAL"))
                .andExpect(jsonPath("$.transactions.length()").value(1))
                .andExpect(jsonPath("$.errorCount").value(6))
                .andExpect(jsonPath("$.errors[0].line").value(3))
                .andExpect(jsonPath("$.errors[0].field").value("date"))
                .andExpect(jsonPath("$.errors[1].line").value(4))
                .andExpect(jsonPath("$.errors[2].field").value("debit"))
                .andExpect(jsonPath("$.errors[2].value").value("12.345"))
                .andExpect(jsonPath("$.errors[3].message").value("a quote is opened and never closed"))
                .andExpect(jsonPath("$.errors[4].message").value("has 3 fields; expected 5"))
                .andExpect(jsonPath("$.errors[5].field").value("description"));
    }

    @Test
    void aFileWithNoGoodLinesIsRejectedAndOnlyTheFirstHundredErrorsAreShown() throws Exception {
        StringBuilder csv = new StringBuilder(HEADER);
        for (int i = 0; i < 150; i++) {
            csv.append("not a date,x,1,,1\n");
        }
        parse(csv.toString())
                .andExpect(jsonPath("$.status").value("REJECTED"))
                .andExpect(jsonPath("$.errorCount").value(150))
                .andExpect(jsonPath("$.errors.length()").value(100));
    }

    @Test
    void aMissingHeaderOrATooLongFileIs422() throws Exception {
        parse("01/04/2026,Rent,25000,,75000\n")
                .andExpect(status().isUnprocessableContent())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("Statement file cannot be read"));
        parse(statement(10_001, 0, null)).andExpect(status().isUnprocessableContent());
        parse(statement(10_000, 0, null)).andExpect(status().isOk());
    }

    @Test
    void anEmptyBodyIs400AndAnotherContentTypeIs415() throws Exception {
        parse("").andExpect(status().isBadRequest());
        mvc.perform(post("/statements/parse").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isUnsupportedMediaType());
    }
}
