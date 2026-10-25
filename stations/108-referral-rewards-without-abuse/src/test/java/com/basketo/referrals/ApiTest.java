package com.basketo.referrals;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.time.Duration;

import static com.basketo.referrals.TestWallet.WALLET;
import static org.awaitility.Awaitility.await;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * The whole app on a real PostgreSQL, with the simulated wallet. The relay polls every 100 ms (1 s in production),
 * waits 500 ms for the wallet (3 s), and gives up after 3 tries 50 ms then 100 ms apart (5 tries from 1 s).
 */
@SpringBootTest(properties = {"basketo.wallet.poll-every=100ms", "basketo.wallet.timeout=500ms",
        "basketo.wallet.max-attempts=3", "basketo.wallet.first-retry-after=50ms"})
@AutoConfigureMockMvc
@Import(PostgresTestConfig.class)
abstract class ApiTest {

    static final JsonMapper JSON = JsonMapper.builder().build();
    static final long PRIYA = 1, KARAN = 2;

    @DynamicPropertySource
    static void wallet(DynamicPropertyRegistry registry) {
        registry.add("basketo.wallet.url", WALLET::url);
    }

    @Autowired
    MockMvc mvc;
    @Autowired
    JdbcClient jdbc;

    @BeforeEach
    void onlyTheDemoCustomers() {
        jdbc.sql("TRUNCATE wallet_outbox, rewards, referrals").update();
        jdbc.sql("DELETE FROM customers WHERE id > 2").update();
        WALLET.reset();
    }

    ResultActions signUp(String code, String phone, String device) throws Exception {
        return mvc.perform(post("/referrals").with(httpBasic("signup", "signup-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                .content("{\"referralCode\":\"" + code + "\",\"name\":\"New Customer\",\"phone\":\"" + phone + "\",\"deviceId\":\"" + device + "\"}"));
    }

    ResultActions order(long orderId, long customer, long totalPaise, String status) throws Exception {
        return mvc.perform(post("/orders/{id}/referral-reward", orderId).with(httpBasic("orders", "orders-demo-pass"))
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"customerId\":" + customer + ",\"totalPaise\":" + totalPaise + ",\"status\":\"" + status + "\"}"));
    }

    static JsonNode json(ResultActions r) throws Exception {
        return JSON.readTree(r.andReturn().getResponse().getContentAsString());
    }

    /** A new customer referred by Priya, signed up on their own device. */
    long referredCustomer(String phone, String device) throws Exception {
        return json(signUp("RIYA100", phone, device)).path("customerId").asLong();
    }

    String delivery(long rewardId) {
        return jdbc.sql("SELECT status FROM wallet_outbox WHERE reward_id = ?").param(rewardId).query(String.class).single();
    }

    String awaitDelivery(long rewardId, String status) {
        return await().atMost(Duration.ofSeconds(10)).pollInterval(Duration.ofMillis(50)).until(() -> delivery(rewardId), status::equals);
    }

    int count(String table) {
        return jdbc.sql("SELECT count(*) FROM " + table).query(Integer.class).single();
    }
}
