package com.tijori.beneficiaries;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.util.concurrent.atomic.AtomicLong;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app, security filters included, called through MockMvc with real HTTP Basic headers. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    private static final AtomicLong NEXT_ACCOUNT = new AtomicLong(50_100_000_000L);

    @Autowired
    MockMvc mvc;

    /** A valid beneficiary with a new account number each time, so tests never collide on the duplicate rule. */
    static String ravisAccount() {
        return """
                {"name":"Ravi Menon","accountNumber":"%d","ifsc":"HDFC0001234"}
                """.formatted(NEXT_ACCOUNT.incrementAndGet());
    }

    ResultActions add(String user, String json) throws Exception {
        return mvc.perform(post("/beneficiaries").with(httpBasic(user, user + "-demo-pass"))
                .contentType(MediaType.APPLICATION_JSON).content(json));
    }
}
