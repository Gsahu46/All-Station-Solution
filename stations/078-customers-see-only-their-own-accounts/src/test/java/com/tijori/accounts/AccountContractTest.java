package com.tijori.accounts;

import org.junit.jupiter.api.Test;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class AccountContractTest extends ApiTest {

    @Test
    void aCustomerSeesTheirAccount() throws Exception {
        account("zoya", 1001).andExpect(status().isOk()).andExpect(jsonPath("$.name").value("Zoya Khan"))
                .andExpect(jsonPath("$.balancePaise").value(9850000)).andExpect(jsonPath("$.kind").value("savings"));
    }

    @Test
    void aMonthsStatementHasItsLinesAndBalancesThatAddUp() throws Exception {
        // Balance now 98,500.00; October's electricity bill (-2,450.00) came after September, so it is added back.
        statement("zoya", 1001, "2026-09").andExpect(status().isOk())
                .andExpect(jsonPath("$.lines[*].description", contains("Salary, Acme Analytics", "Rent, September", "UPI to Dev Patel")))
                .andExpect(jsonPath("$.closingBalancePaise").value(10095000))
                .andExpect(jsonPath("$.openingBalancePaise").value(10095000 - 9500000 + 3200000 + 150000));
    }

    @Test
    void bothHoldersOfAJointAccountSeeIt() throws Exception {
        account("zoya", 1003).andExpect(status().isOk());
        account("dev", 1003).andExpect(status().isOk());
        statement("dev", 1003, "2026-09").andExpect(jsonPath("$.lines[0].amountPaise").value(2500000));
    }

    @Test
    void aMonthWithNoLinesIsEmptyNotAnError() throws Exception {
        statement("zoya", 1001, "2026-08").andExpect(status().isOk()).andExpect(jsonPath("$.lines").isEmpty())
                .andExpect(jsonPath("$.openingBalancePaise").value(3945000)).andExpect(jsonPath("$.closingBalancePaise").value(3945000));
    }

    @Test
    void unknownAccountsAre404AndBadParametersAre400() throws Exception {
        account("zoya", 9999).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No such account"));
        account("zoya", "abc").andExpect(status().isBadRequest());
        statement("zoya", 1001, "2026-13").andExpect(status().isBadRequest());
        statement("zoya", 1001, "September").andExpect(status().isBadRequest());
    }
}
