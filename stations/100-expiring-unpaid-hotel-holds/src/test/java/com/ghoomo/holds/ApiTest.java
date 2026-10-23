package com.ghoomo.holds;

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
import tools.jackson.databind.json.JsonMapper;

import java.time.Clock;
import java.time.Instant;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the whole app on a real PostgreSQL, the demo rooms with nothing held, the expiry job switched off
 * (tests run it themselves) and a clock the test moves.
 */
@SpringBootTest(properties = "ghoomo.holds.expiry.enabled=false")
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    static final Instant T0 = Instant.parse("2026-12-20T10:00:00Z");
    static final TestClock CLOCK = new TestClock(T0);
    static final JsonMapper JSON = JsonMapper.builder().build();

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;
    @Autowired
    Holds holds;

    @TestBean
    Clock clock;

    static Clock clock() {
        return CLOCK;
    }

    @BeforeEach
    void noHoldsAtT0() {
        jdbc.sql("TRUNCATE holds RESTART IDENTITY").update();
        jdbc.sql("UPDATE room_nights SET held = 0").update();
        CLOCK.set(T0);
    }

    ResultActions hold(String key, long roomTypeId, String date, String email) throws Exception {
        var request = post("/holds").contentType(MediaType.APPLICATION_JSON)
                .content("{\"roomTypeId\":" + roomTypeId + ",\"date\":\"" + date + "\",\"guestEmail\":\"" + email + "\"}");
        return mvc.perform(key == null ? request : request.header("Idempotency-Key", key));
    }

    int held(long roomTypeId, String date) {
        return jdbc.sql("SELECT held FROM room_nights WHERE room_type_id = ? AND stay_date = CAST(? AS date)").params(roomTypeId, date).query(Integer.class).single();
    }

    long active(long roomTypeId, String date) {
        return jdbc.sql("SELECT count(*) FROM holds WHERE status = 'HELD' AND room_type_id = ? AND stay_date = CAST(? AS date)").params(roomTypeId, date).query(Long.class).single();
    }
}
