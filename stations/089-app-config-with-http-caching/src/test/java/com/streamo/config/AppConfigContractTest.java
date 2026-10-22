package com.streamo.config;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletResponse;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class AppConfigContractTest extends ApiTest {

    @Test
    void theConfigTellsTheAppWhetherItMustUpdate() throws Exception {
        mvc.perform(config("android", "6.1.0")).andExpect(status().isOk()).andExpect(content().json("""
                {"platform":"android","appVersion":"6.1.0","updateRequired":false,"updateAvailable":true,"latestVersion":"6.2.0","minSupportedVersion":"5.9.0",
                 "features":{"downloads":true,"liveSports":true,"watchParty":false}}"""));
        mvc.perform(config("android", "5.8.9")).andExpect(jsonPath("$.updateRequired").value(true));
        mvc.perform(config("android", "6.2.0")).andExpect(jsonPath("$.updateRequired").value(false)).andExpect(jsonPath("$.updateAvailable").value(false));
        mvc.perform(config("IOS", "5.8.0")).andExpect(jsonPath("$.platform").value("ios")).andExpect(jsonPath("$.updateRequired").value(false));
    }

    @Test
    void versionsAreComparedAsNumbersNotText() throws Exception {
        mvc.perform(config("android", "5.10.0")).andExpect(jsonPath("$.updateRequired").value(false));   // as text, "5.10.0" < "5.9.0"
        mvc.perform(config("android", "5.9.10")).andExpect(jsonPath("$.updateRequired").value(false));
        assertThat(AppVersion.parse("10.0.0")).isGreaterThan(AppVersion.parse("9.99.99"));
    }

    @Test
    void theETagChangesWhenAndOnlyWhenTheAnswerChanges() throws Exception {
        String etag = ask("android", "6.1.0", null).getHeader("ETag");
        assertThat(ask("android", "6.1.0", null).getHeader("ETag")).isEqualTo(etag);
        assertThat(ask("android", "6.0.0", null).getHeader("ETag")).isNotEqualTo(etag);   // appVersion is part of the answer
        assertThat(ask("ios", "6.1.0", null).getHeader("ETag")).isNotEqualTo(etag);
    }

    @Test
    void aPublishedChangeReachesAppsOnTheirNextRevalidation() throws Exception {
        String etag = ask("android", "5.9.5", null).getHeader("ETag");
        configs.publish("android", new AppConfigs.Published("6.3.0", "6.0.0", Map.of("downloads", true), List.of("kids"), Map.of("api", "https://api.streamo.example")));
        MockHttpServletResponse after = ask("android", "5.9.5", etag);
        assertThat(after.getStatus()).isEqualTo(200);
        assertThat(after.getHeader("ETag")).isNotEqualTo(etag);
        assertThat(after.getContentAsString()).contains("\"updateRequired\":true");
    }

    @Test
    void conditionalRequestsFollowHttpRules() throws Exception {
        MockHttpServletResponse first = ask("ios", "6.0.0", null);
        String etag = first.getHeader("ETag");
        MockHttpServletResponse weak = ask("ios", "6.0.0", "W/" + etag);
        assertThat(weak.getStatus()).isEqualTo(304);   // If-None-Match compares weakly
        assertThat(weak.getHeader("ETag")).isEqualTo(etag);
        assertThat(weak.getHeader("Cache-Control")).isEqualTo("max-age=300, public");   // a 304 repeats the caching headers
        assertThat(ask("ios", "6.0.0", "\"other\", " + etag).getStatus()).isEqualTo(304);
        // RFC 9110 (13.1.2) calls for 304 when If-None-Match is * and the resource exists; Spring 7.0.9 answers 200
        // here. Apps never send *, so it is left as it is and recorded. Found while building.
        assertThat(ask("ios", "6.0.0", "*").getStatus()).isEqualTo(200);
        assertThat(ask("ios", "6.0.0", "\"other\"").getStatus()).isEqualTo(200);
    }

    @Test
    void badQueriesAre400() throws Exception {
        mvc.perform(config("windows", "6.1.0")).andExpect(status().isBadRequest());
        mvc.perform(config("android", "6.1")).andExpect(status().isBadRequest());
        mvc.perform(config("android", "6.1.0-beta")).andExpect(status().isBadRequest());
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/app-config").param("platform", "android")).andExpect(status().isBadRequest());
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/app-config/")).andExpect(status().isNotFound());
    }
}
