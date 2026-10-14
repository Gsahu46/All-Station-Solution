package com.tijori.profiles;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.util.List;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/** Shared setup: the whole app through MockMvc, signed in as one of the demo users. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    /** Every full number in the demo data. No response may contain any of them. */
    static final List<String> RAW_NUMBERS = List.of("234567890123", "345678901234", "4111111111111111", "5555555555554444",
            "4012888888881881", "50100012345678", "00011122233344", "9876543210", "9123456780", "asha.rao@example.com", "ravi@example.com");

    @Autowired
    MockMvc mvc;

    ResultActions profileAs(String user, String customerId) throws Exception {
        return mvc.perform(get("/customers/{id}/profile", customerId).with(httpBasic(user, user + "-demo-pass")));
    }
}
