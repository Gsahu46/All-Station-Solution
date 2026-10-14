package com.tijori.statements;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/** Shared setup: the whole app through MockMvc. acc-1001 has 4,000 transactions, acc-1002 none. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    @Autowired
    MockMvc mvc;

    ResultActions transactions(String account, String... params) throws Exception {
        var request = get("/accounts/{id}/transactions", account);
        for (int i = 0; i < params.length; i += 2) {
            request = request.param(params[i], params[i + 1]);
        }
        return mvc.perform(request);
    }
}
