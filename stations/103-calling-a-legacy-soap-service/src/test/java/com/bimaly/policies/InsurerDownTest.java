package com.bimaly.policies;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Nothing listens where the insurer should be (port 1). */
@SpringBootTest(properties = "bimaly.insurer.url=http://127.0.0.1:1/policy")
@AutoConfigureMockMvc
class InsurerDownTest {

    @Autowired
    MockMvc mvc;

    @Test
    void anInsurerThatCannotBeReachedIs502() throws Exception {
        mvc.perform(post("/policies").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"customerName\":\"Meera Iyer\",\"dateOfBirth\":\"1988-04-12\",\"productCode\":\"TERM10\",\"sumInsuredPaise\":1000000000}"))
                .andExpect(status().isBadGateway()).andExpect(jsonPath("$.detail").value("The insurer could not be reached. Try again later."));
    }
}
