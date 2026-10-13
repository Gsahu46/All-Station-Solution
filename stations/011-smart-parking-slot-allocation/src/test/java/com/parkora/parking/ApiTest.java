package com.parkora.parking;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app through MockMvc, a clock the test controls, and an empty building and a reset clock before each test. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(ApiTest.Clocks.class)
abstract class ApiTest {

    @TestConfiguration
    static class Clocks {
        @Bean
        @Primary
        TestClock testClock() {
            return new TestClock();
        }
    }

    @Autowired
    MockMvc mvc;

    @Autowired
    Garage garage;

    @Autowired
    TestClock clock;

    @BeforeEach
    void emptyBuilding() {
        garage.reset();
        clock.reset();
    }

    ResultActions enter(String plate, String type) throws Exception {
        return mvc.perform(post("/parking/entries").contentType(MediaType.APPLICATION_JSON)
                .content("{\"vehicleNumber\":\"" + plate + "\",\"vehicleType\":\"" + type + "\"}"));
    }

    ResultActions exit(String ticketId) throws Exception {
        return mvc.perform(post("/parking/exits/{id}", ticketId));
    }

    String ticketOf(ResultActions entry) throws Exception {
        return com.jayway.jsonpath.JsonPath.read(entry.andReturn().getResponse().getContentAsString(), "$.ticketId");
    }
}
