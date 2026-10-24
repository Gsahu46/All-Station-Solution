package com.bimaly.policies;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static com.bimaly.policies.TestInsurer.INSURER;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** The whole app against the fake insurer, with a 1 s limit on its answers (8 s in production). */
@SpringBootTest(properties = "bimaly.insurer.timeout=1s")
@AutoConfigureMockMvc
abstract class ApiTest {

    @DynamicPropertySource
    static void insurer(DynamicPropertyRegistry registry) {
        registry.add("bimaly.insurer.url", INSURER::url);
    }

    @Autowired
    MockMvc mvc;

    @BeforeEach
    void freshInsurer() {
        INSURER.reset();
    }

    ResultActions issue(String product, long sumPaise) throws Exception {
        return issue("{\"customerName\":\"Meera Iyer\",\"dateOfBirth\":\"1988-04-12\",\"productCode\":\"" + product + "\",\"sumInsuredPaise\":" + sumPaise + "}");
    }

    ResultActions issue(String json) throws Exception {
        return mvc.perform(post("/policies").contentType(MediaType.APPLICATION_JSON).content(json));
    }
}
