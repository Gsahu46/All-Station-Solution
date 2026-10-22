package com.streamo.config;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletResponse;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Written first. The old endpoint sent no ETag and no Cache-Control: every app launch downloaded the whole config
 * again, the same bytes each time. These tests count the bytes 20 launches download.
 */
class EveryLaunchDownloadsTrapTest extends ApiTest {

    @Test
    void anAppThatCannotRevalidateDownloadsEverythingEveryTime() throws Exception {
        long bytes = 0;
        for (int launch = 0; launch < 20; launch++) {
            bytes += ask("android", "6.1.0", null).getContentAsByteArray().length;   // the old app: no If-None-Match to send
        }
        int one = ask("android", "6.1.0", null).getContentAsByteArray().length;
        assertThat(one).isGreaterThan(400);
        assertThat(bytes).isEqualTo(20L * one);
    }

    @Test
    void anAppThatKeepsTheETagDownloadsOnceAndThenGets304s() throws Exception {
        MockHttpServletResponse first = ask("android", "6.1.0", null);
        String etag = first.getHeader("ETag");
        assertThat(etag).matches("\"[A-Za-z0-9_-]{22}\"");
        assertThat(first.getHeader("Cache-Control")).isEqualTo("max-age=300, public");
        long bytes = first.getContentAsByteArray().length;
        for (int launch = 1; launch < 20; launch++) {
            MockHttpServletResponse again = ask("android", "6.1.0", etag);
            assertThat(again.getStatus()).isEqualTo(304);
            bytes += again.getContentAsByteArray().length;
        }
        assertThat(bytes).isEqualTo(first.getContentAsByteArray().length);   // 19 launches downloaded nothing
    }
}
