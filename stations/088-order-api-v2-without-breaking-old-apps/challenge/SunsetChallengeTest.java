package com.kartwala.orders;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.context.bean.override.convention.TestBean;
import org.springframework.test.web.servlet.MockMvc;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Challenge 1: from the sunset date (1 Apr 2027, IST), v1 answers 410 Gone with a link to the migration guide. v2 is unaffected. */
@SpringBootTest
@AutoConfigureMockMvc
class SunsetChallengeTest {

    static volatile Instant now = Instant.parse("2027-03-31T18:29:59Z");   // 23:59:59 IST on 31 Mar 2027

    @TestBean
    Clock clock;

    static Clock clock() {
        return new Clock() {
            public java.time.ZoneId getZone() {
                return ZoneOffset.UTC;
            }

            public Clock withZone(java.time.ZoneId zone) {
                return this;
            }

            public Instant instant() {
                return now;
            }
        };
    }

    @Autowired
    MockMvc mvc;

    @Test
    void v1WorksUntilItsSunsetAndIsGoneFromThen() throws Exception {
        now = Instant.parse("2027-03-31T18:29:59Z");
        mvc.perform(get("/v1/orders/1001")).andExpect(status().isOk());
        now = Instant.parse("2027-03-31T18:30:00Z");   // 00:00 IST on 1 Apr 2027
        mvc.perform(get("/v1/orders/1001")).andExpect(status().isGone())
                .andExpect(jsonPath("$.detail").value("Orders API v1 ended on 1 Apr 2027. Use v2: https://developer.kartwala.example/orders/v1-to-v2"))
                .andExpect(header().string("Link", "<https://developer.kartwala.example/orders/v1-to-v2>; rel=\"deprecation\"; type=\"text/html\""));
        mvc.perform(get("/v2/orders/1001")).andExpect(status().isOk());
    }
}
