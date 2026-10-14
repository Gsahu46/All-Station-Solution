package com.citylibrary.loans;

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

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.util.concurrent.atomic.AtomicReference;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app, fresh demo data, and "today" set by each test (14 Oct 2026 unless moved). */
@SpringBootTest
@AutoConfigureMockMvc
@Import(ApiTest.Today.class)
abstract class ApiTest {

    static final ZoneId IST = ZoneId.of("Asia/Kolkata");
    static final AtomicReference<Instant> NOW = new AtomicReference<>();

    @TestConfiguration
    static class Today {
        @Bean
        @Primary
        Clock today() {
            return new Clock() {
                public Instant instant() {
                    return NOW.get();
                }

                public ZoneId getZone() {
                    return IST;
                }

                public Clock withZone(ZoneId zone) {
                    return this;
                }
            };
        }
    }

    @Autowired
    MockMvc mvc;
    @Autowired
    InMemoryRepositories.Members members;
    @Autowired
    InMemoryRepositories.Loans loans;

    @BeforeEach
    void freshLibrary() {
        NOW.set(Instant.parse("2026-10-14T05:00:00Z"));   // 10:30 in India
        members.reset();
        loans.reset();
    }

    void today(String isoDate) {
        NOW.set(java.time.LocalDate.parse(isoDate).atTime(10, 30).atZone(IST).toInstant());
    }

    ResultActions borrow(String memberId, String bookId) throws Exception {
        return mvc.perform(post("/loans").contentType(MediaType.APPLICATION_JSON)
                .content("{\"memberId\":\"" + memberId + "\",\"bookId\":\"" + bookId + "\"}"));
    }

    ResultActions kiosk(String card, String barcode) throws Exception {
        return mvc.perform(post("/kiosk/checkouts").contentType(MediaType.APPLICATION_JSON)
                .content("{\"cardNumber\":\"" + card + "\",\"barcode\":\"" + barcode + "\"}"));
    }
}
