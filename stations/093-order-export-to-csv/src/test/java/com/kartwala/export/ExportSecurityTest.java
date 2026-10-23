package com.kartwala.export;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class ExportSecurityTest extends ApiTest {

    @Test
    void withoutASignInIt401sAndSupportMayNotExport() throws Exception {
        assertThat(export(null, "2026-01-01", "2026-12-31").getStatus()).isEqualTo(401);
        mvc.perform(get("/seller/orders/export").param("from", "2026-01-01").param("to", "2026-12-31").with(httpBasic("neha.store", "wrong")))
                .andExpect(status().isUnauthorized());
        assertThat(export("sam.help", "2026-01-01", "2026-12-31").getStatus()).isEqualTo(403);
        assertThat(jdbc.sql("SELECT count(*) FROM export_log").query(Long.class).single()).isZero();
    }

    @Test
    void aSellerExportsOnlyTheirOwnOrdersWhateverTheyAddToTheRequest() throws Exception {
        var arun = lines(export("arun.mart", "2026-01-01", "2026-12-31"));
        assertThat(arun).containsExactly(OrderExport.HEADER, "AM-2001,2026-02-11 12:00,Steel bottle,1,499.00,Kochi,DELIVERED");
        var tricked = mvc.perform(get("/seller/orders/export").param("from", "2026-01-01").param("to", "2026-12-31").param("sellerId", "1")
                .with(httpBasic("arun.mart", password("arun.mart")))).andReturn();
        String body = mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.asyncDispatch(tricked)).andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8);
        assertThat(body).doesNotContain("KW-");
    }

    @Test
    void maliciousDatesAreRefused() throws Exception {
        assertThat(export("neha.store", "2026-01-01'; DROP TABLE orders; --", "2026-12-31").getStatus()).isEqualTo(400);
        assertThat(export("neha.store", "../../etc", "2026-12-31").getStatus()).isEqualTo(400);
        assertThat(jdbc.sql("SELECT count(*) FROM orders").query(Long.class).single()).isEqualTo(6);
    }
}
