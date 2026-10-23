package com.chaupal.previews;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

import java.net.InetAddress;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class SsrfSecurityTest extends ApiTest {

    @Test
    void everyWayToNameAnInternalAddressIsRefused() throws Exception {
        for (String url : List.of(
                TestSites.url("127.0.0.1", "/"), TestSites.url("[::1]", "/"), TestSites.url("[::ffff:127.0.0.1]", "/"),
                TestSites.url("0.0.0.0", "/"), "http://169.254.169.254/latest/meta-data/", "http://10.0.0.5/", "http://192.168.1.1/",
                "http://100.64.0.1/", "http://[fd00::1]/", TestSites.url("mixed.example", "/article"),
                TestSites.url("news.example", "/to-metadata"))) {
            preview(url).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.detail").value("This address cannot be previewed"));
        }
    }

    @Test
    void onlyHttpAndHttpsToAHost() throws Exception {
        for (String url : List.of("file:///etc/passwd", "gopher://127.0.0.1:6379/_INFO", "ftp://news.example/", "http:///nohost",
                "http://user:pass@" + "news.example:" + TestSites.PORT + "/article", "javascript:alert(1)")) {
            preview(url).andExpect(status().isBadRequest());
        }
        preview(TestSites.url("news.example", "/to-file")).andExpect(status().isUnprocessableContent());   // a redirect to file: is not followed
    }

    @Test
    void theAddressRulesOneByOne() throws Exception {
        AddressPolicy p = new AddressPolicy(List.of());
        for (String blocked : List.of("127.0.0.1", "10.1.2.3", "172.16.0.1", "172.31.255.255", "192.168.0.1", "169.254.169.254", "0.0.0.0",
                "100.64.0.1", "100.127.255.255", "224.0.0.1", "::1", "fe80::1", "fd12:3456::1", "::ffff:10.0.0.1")) {
            assertThat(p.isBlocked(InetAddress.getByName(blocked))).as(blocked).isTrue();
        }
        for (String open : List.of("8.8.8.8", "172.32.0.1", "100.128.0.1", "2001:4860:4860::8888", "::ffff:8.8.8.8")) {
            assertThat(p.isBlocked(InetAddress.getByName(open))).as(open).isFalse();
        }
    }

    @Test
    void signInRulesAndAnotherMembersPreview() throws Exception {
        mvc.perform(post("/link-previews").contentType("application/json").content("{\"url\":\"http://news.example/\"}")).andExpect(status().isUnauthorized());
        preview("guest", TestSites.url("news.example", "/article")).andExpect(status().isForbidden());
        String body = preview("meera", TestSites.url("news.example", "/article")).andReturn().getResponse().getContentAsString();
        String id = JsonMapper.builder().build().readTree(body).get("id").asString();
        read("dev", id).andExpect(status().isNotFound());   // Meera's draft preview is hers
        read("meera", id).andExpect(status().isOk());
    }
}
