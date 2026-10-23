package com.tiffino.orders;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.core.annotation.Order;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.net.URI;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

/** Twenty phones open the order screen, then the users lock them. Written first. */
@Import(LeakingStreamsTrapTest.OldWay.class)
class LeakingStreamsTrapTest extends ApiTest {

    /** The old way: an emitter that never times out, kept in a list that nothing ever removes from. */
    @TestConfiguration
    static class OldWay {
        static final List<SseEmitter> STREAMS = new CopyOnWriteArrayList<>();

        @RestController   // a member of this configuration: registered with it
        static class OldStream {
            @GetMapping("/old/orders/1001/events")
            SseEmitter events() throws java.io.IOException {
                SseEmitter emitter = new SseEmitter(0L);   // 0: no timeout
                emitter.send("PLACED");
                STREAMS.add(emitter);
                return emitter;
            }
        }

        @Bean
        @Order(0)
        SecurityFilterChain oldWayIsOpen(HttpSecurity http) throws Exception {
            return http.securityMatcher("/old/**").authorizeHttpRequests(a -> a.anyRequest().permitAll()).build();
        }
    }

    @Test
    void theOldWayKeepsEveryStreamOfEveryClientThatLeft() throws Exception {
        List<AutoCloseable> phones = new ArrayList<>();
        for (int i = 0; i < 20; i++) {
            var response = HTTP.send(HttpRequest.newBuilder(URI.create("http://localhost:" + port + "/old/orders/1001/events")).build(),
                    HttpResponse.BodyHandlers.ofInputStream());
            phones.add(response.body());
        }
        for (AutoCloseable phone : phones) {
            phone.close();   // locked: the connection is gone from the phone's side
        }
        // Nothing ever ends these streams or removes them: twenty dead clients, held for as long as the server runs.
        await().during(Duration.ofSeconds(4)).atMost(Duration.ofSeconds(5)).until(() -> OldWay.STREAMS.size() == 20);
    }

    @Test
    void theApiLetsGoOfClientsThatLeft() throws Exception {
        int before = streams.streams();
        List<Stream> phones = new ArrayList<>();
        for (int i = 0; i < 20; i++) {
            phones.add(open("riya", 1001, null));
        }
        phones.forEach(p -> p.awaitEvents(1));
        assertThat(streams.streams()).isEqualTo(before + 20);
        for (Stream phone : phones) {
            phone.close();
        }
        // The next heartbeats write to them, the writes fail, and they are dropped. (Every 15 s in production.)
        await().atMost(Duration.ofSeconds(5)).until(() -> {
            streams.heartbeat();
            return streams.streams() == before;
        });
    }
}
