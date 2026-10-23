package com.kartwala.export;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.test.web.servlet.MvcResult;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.asyncDispatch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/** Challenge 1: ?status=PLACED (optional) exports only orders in that state; an unknown state is 400. */
class StatusFilterChallengeTest extends ApiTest {

    MockHttpServletResponse exportWithStatus(String status) throws Exception {
        MvcResult started = mvc.perform(get("/seller/orders/export").param("from", "2026-01-01").param("to", "2026-12-31").param("status", status)
                .with(httpBasic("neha.store", password("neha.store")))).andReturn();
        return started.getRequest().isAsyncStarted() ? mvc.perform(asyncDispatch(started)).andReturn().getResponse() : started.getResponse();
    }

    @Test
    void onlyOrdersInThatState() throws Exception {
        var placed = lines(exportWithStatus("PLACED"));
        assertThat(placed).hasSize(3).first().isEqualTo(OrderExport.HEADER);
        assertThat(placed.subList(1, 3)).allMatch(l -> l.endsWith(",PLACED"));
        assertThat(lines(export("neha.store", "2026-01-01", "2026-12-31"))).hasSize(6);   // without it, every state
    }

    @Test
    void anUnknownStateIs400() throws Exception {
        assertThat(exportWithStatus("LOST").getStatus()).isEqualTo(400);
    }
}
