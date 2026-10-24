package com.kartwala.refunds;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import tools.jackson.databind.json.JsonMapper;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** The whole app on a real PostgreSQL. Every test starts with no refunds on the three demo orders. */
@SpringBootTest
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    static final JsonMapper JSON = JsonMapper.builder().build();
    static final long WASHING_MACHINE = 5001, MIXER = 5002, PHONE = 5003;   // ₹12,500, ₹4,999, ₹20,000

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void noRefunds() {
        jdbc.sql("TRUNCATE refunds RESTART IDENTITY").update();
        jdbc.sql("UPDATE orders SET reserved_paise = 0").update();
    }

    ResultActions refund(long order, long paise, String agent) throws Exception {
        return mvc.perform(post("/orders/{id}/refunds", order).with(httpBasic(agent, agent + "-demo-pass"))
                .contentType(MediaType.APPLICATION_JSON).content("{\"amountPaise\":" + paise + ",\"reason\":\"Damaged on delivery\"}"));
    }

    ResultActions decide(long refund, String decision, String approver) throws Exception {
        return mvc.perform(post("/refunds/{id}/approvals", refund).with(httpBasic(approver, approver + "-demo-pass"))
                .contentType(MediaType.APPLICATION_JSON).content("{\"decision\":\"" + decision + "\",\"note\":\"Checked with the customer\"}"));
    }

    long idOf(ResultActions created) throws Exception {
        return JSON.readTree(created.andReturn().getResponse().getContentAsString()).path("id").asLong();
    }

    long reserved(long order) {
        return jdbc.sql("SELECT reserved_paise FROM orders WHERE id = ?").param(order).query(Long.class).single();
    }

    /** The sum the rule is about, counted from the refunds themselves: approved and waiting. */
    long refundedOrPending(long order) {
        return jdbc.sql("SELECT COALESCE(SUM(amount_paise), 0) FROM refunds WHERE order_id = ? AND status <> 'REJECTED'").param(order)
                .query(Long.class).single();
    }
}
