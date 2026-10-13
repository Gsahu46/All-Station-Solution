package com.chaupal.comments;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import tools.jackson.databind.json.JsonMapper;

import java.util.Map;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

/** Shared setup: the whole app with security, through MockMvc. No comments and a fresh rate limit before each test. */
@SpringBootTest
@AutoConfigureMockMvc
abstract class ApiTest {

    static final JsonMapper JSON = JsonMapper.builder().build();

    @Autowired
    MockMvc mvc;

    @Autowired
    CommentService service;

    @Autowired
    RateLimiter rateLimiter;

    @BeforeEach
    void cleanSlate() {
        service.clear();
        rateLimiter.reset();
    }

    /** JSON built by Jackson, so payloads full of quotes and angle brackets arrive exactly as written. */
    static String body(String text) {
        return JSON.writeValueAsString(Map.of("text", text));
    }

    ResultActions comment(String user, long postId, String text) throws Exception {
        return mvc.perform(post("/posts/{id}/comments", postId).with(httpBasic(user, user + "-demo-pass"))
                .contentType(MediaType.APPLICATION_JSON).content(body(text)));
    }

    String html(long postId) throws Exception {
        return mvc.perform(get("/posts/{id}/comments", postId).accept(MediaType.TEXT_HTML))
                .andReturn().getResponse().getContentAsString();
    }
}
