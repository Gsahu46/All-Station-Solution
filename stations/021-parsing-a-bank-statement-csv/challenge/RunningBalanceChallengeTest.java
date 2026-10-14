package com.tijori.statementimport;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * Challenge 1: each line's balance must be the line before's balance, minus its debit, plus its credit.
 * A mismatch is an error on that line saying what the balance should be. After a line that could not be read,
 * the next line is not checked (there is nothing reliable to compare with). Each line follows the balance the
 * file states on the line before, so one wrong balance is one error, not a cascade.
 */
class RunningBalanceChallengeTest extends ApiTest {

    @Test
    void aBalanceThatDoesNotFollowIsAnError() throws Exception {
        parse(HEADER + """
                01/04/2026,Opening,,1000,1000
                02/04/2026,Rent,250,,750
                03/04/2026,Groceries,100.50,,649.50
                04/04/2026,Refund,,49.50,700.00
                05/04/2026,Fuel,200,,500.00
                """)
                .andExpect(jsonPath("$.status").value("PARTIAL"))
                .andExpect(jsonPath("$.errorCount").value(1))
                .andExpect(jsonPath("$.errors[0].line").value(5))
                .andExpect(jsonPath("$.errors[0].field").value("balance"))
                .andExpect(jsonPath("$.errors[0].message").value("should be 699.00 (649.50 - 0.00 + 49.50)"));
    }

    @Test
    void theLineAfterAnUnreadableLineIsNotChecked() throws Exception {
        parse(HEADER + """
                01/04/2026,Opening,,1000,1000
                bad date,Rent,250,,750
                03/04/2026,Groceries,100,,650
                04/04/2026,Fuel,50,,600
                """)
                .andExpect(jsonPath("$.errorCount").value(1))
                .andExpect(jsonPath("$.errors[0].field").value("date"));
    }
}
