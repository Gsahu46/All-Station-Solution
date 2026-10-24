package com.seatsure.sales;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.system.CapturedOutput;
import org.springframework.boot.test.system.OutputCaptureExtension;

import javax.sql.DataSource;
import java.sql.Connection;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

import static com.seatsure.sales.TestGateway.GATEWAY;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The failure drills from the runbook, as tests: a gateway that hangs, and a pool with nothing left. */
@ExtendWith(OutputCaptureExtension.class)
class OperationsDrillTest extends ApiTest {

    @Autowired
    DataSource dataSource;

    @Test
    void aHangingGatewayIsCutOffAndTheDatabaseStaysFree() throws Exception {
        GATEWAY.delayMillis = 3_000;   // longer than the 1 s limit here (3 s in production)
        double before = poolTimeouts();
        List<Future<Integer>> fans = new ArrayList<>();
        try (var threads = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 8; i++) {
                fans.add(threads.submit(() -> order(1, "fan", 1).andReturn().getResponse().getStatus()));
            }
            // While the eight charges hang at the gateway, the rest of the app answers at once.
            org.awaitility.Awaitility.await().atMost(java.time.Duration.ofSeconds(2)).until(() -> GATEWAY.idempotencyKeys.size() == 8);
            long started = System.nanoTime();
            mvc.perform(get("/sales/1")).andExpect(status().isOk());
            assertThat((System.nanoTime() - started) / 1_000_000).isLessThan(500);
        }
        assertThat(fans).extracting(Future::resultNow).containsOnly(504);
        assertThat(sold(1)).isZero();   // every seat given back
        assertThat(poolTimeouts()).isEqualTo(before);
    }

    @Test
    void withNoConnectionFreeTheAnswerIs503AfterOneSecondNotThirty(CapturedOutput output) throws Exception {
        List<Connection> taken = new ArrayList<>();
        try {
            for (int i = 0; i < 4; i++) {
                taken.add(dataSource.getConnection());   // something else holds the whole pool
            }
            long started = System.nanoTime();
            order(1, "fan", 1).andExpect(status().isServiceUnavailable()).andExpect(header().string("Retry-After", "5"))
                    .andExpect(jsonPath("$.detail").value("Too busy right now. Try again in a few seconds."));
            assertThat((System.nanoTime() - started) / 1_000_000).isBetween(900L, 3_000L);
            assertThat(output.getOut()).contains("No database connection within the pool's timeout");
        } finally {
            for (Connection c : taken) {
                c.close();
            }
        }
        order(1, "fan", 1).andExpect(status().isCreated());   // and it recovers by itself
    }

    @Test
    void theMetricsTheAlertsReadArePublished() throws Exception {
        for (String metric : new String[]{"hikaricp.connections.pending", "hikaricp.connections.timeout", "hikaricp.connections.usage"}) {
            mvc.perform(get("/actuator/metrics/" + metric)).andExpect(status().isOk()).andExpect(jsonPath("$.name").value(metric));
        }
    }
}
