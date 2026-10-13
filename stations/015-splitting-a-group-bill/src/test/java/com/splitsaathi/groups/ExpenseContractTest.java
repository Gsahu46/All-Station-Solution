package com.splitsaathi.groups;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: three kinds of split, settle-up, and every way an expense can be refused. */
class ExpenseContractTest extends ApiTest {

    @Test
    void anExactSplitIsStoredAsGiven() throws Exception {
        expense(1, """
                {"description":"Hotel","paidBy":"ravi","amountPaise":1200000,"splitType":"EXACT",
                 "exactPaise":{"asha":500000,"ravi":400000,"meera":300000}}""")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").isNotEmpty())
                .andExpect(jsonPath("$.owedPaise.asha").value(500000))
                .andExpect(jsonPath("$.owedPaise.meera").value(300000));
    }

    @Test
    void sharesSplitByWeight() throws Exception {
        expense(1, """
                {"description":"Fuel","paidBy":"kabir","amountPaise":100000,"splitType":"SHARES","shares":{"kabir":2,"asha":1,"ravi":1}}""")
                .andExpect(jsonPath("$.owedPaise.kabir").value(50000))
                .andExpect(jsonPath("$.owedPaise.asha").value(25000))
                .andExpect(jsonPath("$.owedPaise.ravi").value(25000));
    }

    @Test
    void settleUpNeedsAtMostOneFewerPaymentThanPeople() throws Exception {
        // Six expenses that, settled one by one, would need a dozen transfers.
        String[] trip = {
                "{\"description\":\"Train\",\"paidBy\":\"asha\",\"amountPaise\":480000,\"splitType\":\"EQUAL\",\"participants\":[\"asha\",\"kabir\",\"meera\",\"ravi\"]}",
                "{\"description\":\"Hotel\",\"paidBy\":\"ravi\",\"amountPaise\":1200000,\"splitType\":\"EQUAL\",\"participants\":[\"asha\",\"kabir\",\"meera\",\"ravi\"]}",
                "{\"description\":\"Scooters\",\"paidBy\":\"kabir\",\"amountPaise\":160000,\"splitType\":\"EQUAL\",\"participants\":[\"asha\",\"kabir\",\"meera\",\"ravi\"]}",
                "{\"description\":\"Dinner\",\"paidBy\":\"meera\",\"amountPaise\":300000,\"splitType\":\"EQUAL\",\"participants\":[\"asha\",\"kabir\",\"meera\",\"ravi\"]}",
                "{\"description\":\"Snacks\",\"paidBy\":\"asha\",\"amountPaise\":20000,\"splitType\":\"EQUAL\",\"participants\":[\"asha\",\"meera\"]}",
                "{\"description\":\"Boat\",\"paidBy\":\"kabir\",\"amountPaise\":100000,\"splitType\":\"SHARES\",\"shares\":{\"kabir\":1,\"ravi\":1}}"};
        for (String e : trip) {
            expense(1, e).andExpect(status().isCreated());
        }
        mvc.perform(get("/groups/1/settle-up"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.balancesPaise.ravi").value(1200000 - (120000 + 300000 + 40000 + 75000 + 50000)))
                .andExpect(jsonPath("$.payments", hasSize(3)));
    }

    @Test
    void aGroupWithNoExpensesHasNothingToSettle() throws Exception {
        mvc.perform(get("/groups/2/settle-up")).andExpect(jsonPath("$.payments", hasSize(0)))
                .andExpect(jsonPath("$.balancesPaise.neha").value(0));
    }

    @Test
    void exactAmountsThatDoNotAddUpAre422() throws Exception {
        expense(1, """
                {"description":"Hotel","paidBy":"ravi","amountPaise":1200000,"splitType":"EXACT","exactPaise":{"asha":500000,"ravi":400000}}""")
                .andExpect(status().isUnprocessableContent())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.detail").value("The exact amounts add up to 900000 paise, not 1200000."));
    }

    @Test
    void someoneOutsideTheGroupIs422() throws Exception {
        expense(1, """
                {"description":"Dinner","paidBy":"asha","amountPaise":1000,"splitType":"EQUAL","participants":["asha","neha"]}""")
                .andExpect(status().isUnprocessableContent());
        expense(1, """
                {"description":"Dinner","paidBy":"neha","amountPaise":1000,"splitType":"EQUAL","participants":["asha"]}""")
                .andExpect(status().isUnprocessableContent());
    }

    @Test
    void badSplitsAre422() throws Exception {
        expense(1, """
                {"description":"x","paidBy":"asha","amountPaise":1000,"splitType":"EQUAL","participants":["asha","asha"]}""")
                .andExpect(status().isUnprocessableContent());
        expense(1, """
                {"description":"x","paidBy":"asha","amountPaise":1000,"splitType":"SHARES","shares":{"asha":0}}""")
                .andExpect(status().isUnprocessableContent());
        expense(1, """
                {"description":"x","paidBy":"asha","amountPaise":1000,"splitType":"EQUAL"}""")
                .andExpect(status().isUnprocessableContent());
    }

    @Test
    void badFieldsAre400() throws Exception {
        expense(1, """
                {"description":"x","paidBy":"asha","amountPaise":0,"splitType":"EQUAL","participants":["asha"]}""")
                .andExpect(status().isBadRequest());
        expense(1, """
                {"description":"x","paidBy":"asha","amountPaise":1000.5,"splitType":"EQUAL","participants":["asha"]}""")
                .andExpect(status().isBadRequest());
        expense(1, """
                {"description":"x","paidBy":"asha","amountPaise":1000,"splitType":"HALF","participants":["asha"]}""")
                .andExpect(status().isBadRequest());
    }

    @Test
    void anUnknownGroupIs404() throws Exception {
        mvc.perform(get("/groups/99/settle-up")).andExpect(status().isNotFound())
                .andExpect(jsonPath("$.title").value("Group not found"));
    }
}
