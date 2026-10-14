package com.tijori.statementimport;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: find columns by name, in any order, with other banks' names for them:
 * "Txn Date", "Narration", "Withdrawal Amt", "Deposit Amt", "Closing Balance". Extra columns are ignored.
 */
class ColumnsByNameChallengeTest extends ApiTest {

    @Test
    void anotherBanksHeaderInAnotherOrderIsRead() throws Exception {
        parse("""
                Narration,Txn Date,Ref No,Deposit Amt,Withdrawal Amt,Closing Balance
                Salary,01/04/2026,REF1,"1,20,000",,120000
                Rent,02/04/2026,REF2,,25000,95000
                """)
                .andExpect(jsonPath("$.status").value("COMPLETE"))
                .andExpect(jsonPath("$.transactions[0].description").value("Salary"))
                .andExpect(jsonPath("$.transactions[0].creditPaise").value(12000000))
                .andExpect(jsonPath("$.transactions[1].debitPaise").value(2500000));
    }

    @Test
    void aMissingColumnIs422NamingIt() throws Exception {
        parse("""
                Txn Date,Narration,Withdrawal Amt,Deposit Amt
                01/04/2026,Salary,,1000
                """)
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.detail").value("The header has no balance column (also accepted: closing balance)."));
    }
}
