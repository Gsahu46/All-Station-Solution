package com.tiffino.reports;

import org.junit.jupiter.api.Test;
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

import java.time.Clock;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract, with the fixture day as the sales feed and the clock at 11:30 on 15 October in India. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(DailySalesContractTest.FixtureBeans.class)
class DailySalesContractTest {

    @TestConfiguration
    static class FixtureBeans {
        @Bean
        @Primary
        SalesFeed fixtureFeed() {
            return Fixture.FEED;
        }

        @Bean
        @Primary
        Clock fixtureClock() {
            return Fixture.CLOCK;
        }
    }

    @Autowired
    MockMvc mvc;

    ResultActions report(String date) throws Exception {
        return mvc.perform(date == null ? get("/reports/daily-sales") : get("/reports/daily-sales").param("date", date));
    }

    @Test
    void aClosedDayHasTotalsPerOutletAndPerHour() throws Exception {
        report("2026-10-14").andExpect(status().isOk())
                .andExpect(content().json("""
                        {"date":"2026-10-14","chainTotalPaise":169660,"bills":7,
                         "outlets":[
                           {"outletId":"TF-01","name":"Tiffino Koramangala","totalPaise":94380,"bills":3,"busiestHour":13},
                           {"outletId":"TF-03","name":"Tiffino HSR Layout","totalPaise":45890,"bills":2,"busiestHour":20},
                           {"outletId":"TF-02","name":"Tiffino Indiranagar","totalPaise":29390,"bills":2,"busiestHour":12}],
                         "hours":[
                           {"hour":0,"totalPaise":9245,"bills":1},{"hour":9,"totalPaise":41885,"bills":2},
                           {"hour":12,"totalPaise":29390,"bills":2},{"hour":13,"totalPaise":52495,"bills":1},
                           {"hour":20,"totalPaise":36645,"bills":1}]}""", org.springframework.test.json.JsonCompareMode.STRICT));
    }

    @Test
    void aDayWithNoSalesIs404() throws Exception {
        report("2026-10-10").andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON))
                .andExpect(jsonPath("$.title").value("No sales"));
    }

    @Test
    void todayAndTheFutureAre422() throws Exception {
        report("2026-10-15").andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Day not over"));
        report("2027-01-01").andExpect(status().isUnprocessableContent());
    }

    @Test
    void aMissingOrMalformedDateIs400() throws Exception {
        report(null).andExpect(status().isBadRequest());
        report("14-10-2026").andExpect(status().isBadRequest());
        report("2026-02-30").andExpect(status().isBadRequest());
    }
}
