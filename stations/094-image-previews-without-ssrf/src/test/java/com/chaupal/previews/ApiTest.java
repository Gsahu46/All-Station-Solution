package com.chaupal.previews;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.convention.TestBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/**
 * Shared setup: the whole app, with the test DNS and the "public" test site allowed although it is on 127.0.0.2.
 * The "internal" one on 127.0.0.1 stays blocked, like every private address.
 */
@SpringBootTest(properties = "chaupal.previews.allowed-private-addresses=127.0.0.2")
@AutoConfigureMockMvc
abstract class ApiTest {

    @Autowired
    MockMvc mvc;

    @TestBean
    NameLookup nameLookup;

    static NameLookup nameLookup() {
        return TestSites::lookup;
    }

    static String password(String user) {
        return user + "-demo-pass";
    }

    ResultActions preview(String user, String url) throws Exception {
        return mvc.perform(post("/link-previews").with(httpBasic(user, password(user))).contentType(MediaType.APPLICATION_JSON)
                .content("{\"url\":\"" + url.replace("\\", "\\\\").replace("\"", "\\\"") + "\"}"));
    }

    ResultActions preview(String url) throws Exception {
        return preview("meera", url);
    }

    ResultActions read(String user, String id) throws Exception {
        return mvc.perform(get("/link-previews/{id}", id).with(httpBasic(user, password(user))));
    }
}
