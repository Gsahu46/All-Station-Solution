package com.kartwala.recent;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.server.context.WebServerApplicationContext;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * Kartwala runs two servers behind a load balancer. Each request may land on either one.
 * This test starts two real copies of the app, on two ports, and plays the load balancer.
 */
class PerServerCacheTrapTest {

    static ConfigurableApplicationContext serverA, serverB;
    static List<RestClient> servers;

    @BeforeAll
    static void startTwoServers() {
        serverA = new SpringApplicationBuilder(RecentlyViewedApplication.class).properties("server.port=0").run();
        serverB = new SpringApplicationBuilder(RecentlyViewedApplication.class).properties("server.port=0").run();
        servers = List.of(client(serverA), client(serverB));
    }

    @AfterAll
    static void stopServers() {
        serverA.close();
        serverB.close();
    }

    static RestClient client(ConfigurableApplicationContext app) {
        int port = ((WebServerApplicationContext) app).getWebServer().getPort();
        return RestClient.create("http://localhost:" + port);
    }

    static void view(RestClient server, long user, long product) {
        server.post().uri("/users/{id}/recently-viewed", user).contentType(MediaType.APPLICATION_JSON)
                .body(Map.of("productId", product)).retrieve().toBodilessEntity();
    }

    @SuppressWarnings("unchecked")
    static List<Integer> history(RestClient server, long user) {
        return (List<Integer>) server.get().uri("/users/{id}/recently-viewed", user).retrieve().body(Map.class).get("productIds");
    }

    @Test
    void roundRobinSendsTheReadToTheServerThatNeverSawTheViews() {
        // The "before" assumption: the in-memory history is "the" history. Round robin: A, B, A, B...
        view(servers.get(0), 7, 501);
        view(servers.get(1), 7, 502);
        assertThat(history(servers.get(0), 7)).containsExactly(501); // the strip shows half the history
        assertThat(history(servers.get(1), 7)).containsExactly(502); // and a different half on the next refresh
    }

    @Test
    void routingEachUserToOneServerKeepsTheirHistoryTogether() {
        // The fix this station can make without new infrastructure: the load balancer sends a user to the same
        // server every time (sticky routing by user id). Its limits are on the page: a restart or a new server
        // loses or moves histories. A shared store (Valkey, a later station) removes them.
        RestClient home = servers.get((int) (8 % servers.size()));
        view(home, 8, 601);
        view(home, 8, 602);
        assertThat(history(home, 8)).containsExactly(602, 601);
    }
}
