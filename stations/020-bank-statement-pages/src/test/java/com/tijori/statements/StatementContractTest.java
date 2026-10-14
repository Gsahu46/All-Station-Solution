package com.tijori.statements;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: the first, last and past-the-end pages, the limits, and unknown accounts. */
class StatementContractTest extends ApiTest {

    @Test
    void theFirstPageIsTheNewestTwenty() throws Exception {
        transactions("ACC-1001")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items", hasSize(20)))
                .andExpect(jsonPath("$.items[0].id").value(3998))
                .andExpect(jsonPath("$.items[0].postedAt").value("2026-10-02T18:45:00"))
                .andExpect(jsonPath("$.page").value(0))
                .andExpect(jsonPath("$.size").value(20))
                .andExpect(jsonPath("$.totalItems").value(4000))
                .andExpect(jsonPath("$.totalPages").value(200))
                .andExpect(jsonPath("$.hasNext").value(true))
                .andExpect(jsonPath("$.lastId").value(3979));
    }

    @Test
    void theLastPageHasNoNextAndPastTheEndIsEmpty() throws Exception {
        transactions("acc-1001", "page", "39", "size", "100")
                .andExpect(jsonPath("$.items", hasSize(100)))
                .andExpect(jsonPath("$.hasNext").value(false));
        transactions("acc-1001", "page", "40", "size", "100")
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.items", hasSize(0)))
                .andExpect(jsonPath("$.hasNext").value(false))
                .andExpect(jsonPath("$.lastId").doesNotExist());
    }

    @Test
    void anAccountWithNoTransactionsHasNoPages() throws Exception {
        transactions("acc-1002").andExpect(jsonPath("$.items", hasSize(0))).andExpect(jsonPath("$.totalPages").value(0));
    }

    @Test
    void outOfRangeParametersAre400() throws Exception {
        transactions("acc-1001", "size", "100").andExpect(status().isOk());
        transactions("acc-1001", "size", "101").andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
        transactions("acc-1001", "size", "0").andExpect(status().isBadRequest());
        transactions("acc-1001", "page", "-1").andExpect(status().isBadRequest());
        transactions("acc-1001", "page", "abc").andExpect(status().isBadRequest());
        transactions("acc-1001", "page", "99", "size", "100").andExpect(status().isOk());          // offset 9,900
        transactions("acc-1001", "page", "100", "size", "100").andExpect(status().isBadRequest()); // offset 10,000
    }

    @Test
    void anUnknownAccountIs404() throws Exception {
        transactions("acc-9999").andExpect(status().isNotFound()).andExpect(jsonPath("$.title").value("Account not found"));
    }
}
