package com.tijori.wallets;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.bean.override.convention.TestBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app on a real PostgreSQL, a clock the tests set, and the demo wallets exactly as V2 creates them. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    /** Noon in India on 30 Oct 2026. */
    static final Instant NOON_IST = Instant.parse("2026-10-30T06:30:00Z");
    static final long ANANYA = 1001;   // minimum KYC: ₹10,000 a day
    static final long VIKRAM = 1002;   // full KYC: ₹1,00,000 a day

    static final class TestClock extends Clock {
        volatile Instant now = NOON_IST;

        @Override
        public ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            return this;
        }

        @Override
        public Instant instant() {
            return now;
        }
    }

    static final TestClock CLOCK = new TestClock();

    @TestBean
    Clock clock;

    static Clock clock() {
        return CLOCK;
    }

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void demoWallets() throws Exception {
        CLOCK.now = NOON_IST;
        jdbc.sql("TRUNCATE kyc_tiers, wallets, top_ups RESTART IDENTITY").update();
        jdbc.sql(Files.readString(Path.of("src/main/resources/db/migration/V2__demo_wallets.sql"))).update();
    }

    ResultActions topUp(long wallet, String json) throws Exception {
        return mvc.perform(post("/wallets/{id}/top-ups", wallet).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    ResultActions topUp(long wallet, long amountPaise) throws Exception {
        return topUp(wallet, "{\"amountPaise\":" + amountPaise + "}");
    }

    long toppedUp(long wallet) {
        return jdbc.sql("SELECT coalesce(sum(amount_paise), 0) FROM top_ups WHERE wallet_id = ?").param(wallet).query(Long.class).single();
    }

    long balance(long wallet) {
        return jdbc.sql("SELECT balance_paise FROM wallets WHERE id = ?").param(wallet).query(Long.class).single();
    }
}
