package com.dakroute.tracking;

import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import org.junit.jupiter.api.Test;
import org.slf4j.MDC;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station: it reproduces the bug before the fix. Both requests run on one thread,
 * as they do in a server's thread pool, one after another.
 */
class LeakedRequestIdTrapTest {

    /** The "before" code: put the caller's id in the MDC when there is one; never clear it. Kept only in tests. */
    static void oldFilter(HttpServletRequest request, Runnable handler) {
        String id = request.getHeader("X-Request-Id");
        if (id != null) {
            MDC.put("requestId", id);
        }
        handler.run();
    }

    static MockHttpServletRequest request(String requestId) {
        MockHttpServletRequest r = new MockHttpServletRequest("GET", "/shipments/DKR100000001IN");
        if (requestId != null) {
            r.addHeader("X-Request-Id", requestId);
        }
        return r;
    }

    @Test
    void theOldFilterLetsTheNextRequestLogTheLastOnesId() {
        List<String> logged = new ArrayList<>();
        oldFilter(request("customer-a-0001"), () -> logged.add(MDC.get("requestId")));
        oldFilter(request(null), () -> logged.add(MDC.get("requestId")));        // a client that sends no id
        assertThat(logged).containsExactly("customer-a-0001", "customer-a-0001");   // B's lines are filed under A
        MDC.clear();
    }

    @Test
    void theRealFilterGivesEachRequestItsOwnIdAndLeavesNothingBehind() throws Exception {
        RequestIdFilter filter = new RequestIdFilter();
        List<String> logged = new ArrayList<>();
        FilterChain chain = (req, res) -> logged.add(MDC.get("requestId"));
        filter.doFilter(request("customer-a-0001"), new MockHttpServletResponse(), chain);
        MockHttpServletResponse second = new MockHttpServletResponse();
        filter.doFilter(request(null), second, chain);
        assertThat(logged.get(0)).isEqualTo("customer-a-0001");
        assertThat(logged.get(1)).isNotEqualTo("customer-a-0001").isEqualTo(second.getHeader("X-Request-Id"));
        assertThat(MDC.get("requestId")).isNull();
    }

    @Test
    void theIdIsClearedEvenWhenTheRequestFails() {
        RequestIdFilter filter = new RequestIdFilter();
        FilterChain failing = (req, res) -> {
            throw new IllegalStateException("handler failed");
        };
        try {
            filter.doFilter(request("customer-b-0002"), new MockHttpServletResponse(), failing);
        } catch (Exception expected) {
            // the failure itself is not the point here
        }
        assertThat(MDC.get("requestId")).isNull();
    }
}
