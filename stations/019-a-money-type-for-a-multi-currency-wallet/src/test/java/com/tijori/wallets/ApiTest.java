package com.tijori.wallets;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app through MockMvc, every wallet empty before each test. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    @Autowired
    MockMvc mvc;

    @Autowired
    WalletController wallets;

    @BeforeEach
    void emptyWallets() {
        wallets.clear();
    }

    ResultActions credit(String wallet, String amount, String currency) throws Exception {
        return mvc.perform(post("/wallets/{id}/credits", wallet).contentType(MediaType.APPLICATION_JSON).content(
                "{\"amount\":\"" + amount + "\",\"currency\":\"" + currency + "\",\"reference\":\"test\"}"));
    }

    ResultActions balance(String wallet) throws Exception {
        return mvc.perform(get("/wallets/{id}/balance", wallet));
    }
}
