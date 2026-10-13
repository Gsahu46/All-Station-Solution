package com.chaupal.comments;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.web.util.HtmlUtils;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.not;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Security: 401, 403, another user's private post, and malicious input of the kinds attackers actually send. */
class CommentSecurityTest extends ApiTest {

    @Test
    void postingWithoutSigningInIs401() throws Exception {
        mvc.perform(post("/posts/1/comments").contentType(MediaType.APPLICATION_JSON).content(body("hi")))
                .andExpect(status().isUnauthorized())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
    }

    @Test
    void aMutedUserCanReadButNotPost403() throws Exception {
        comment("tara", 1, "Let me in").andExpect(status().isForbidden())
                .andExpect(jsonPath("$.type").value("https://chaupal.example/problems/forbidden"));
        mvc.perform(get("/posts/1/comments").with(httpBasic("tara", "tara-demo-pass"))).andExpect(status().isOk());
    }

    @Test
    void anotherUsersPrivatePostLooksLikeItDoesNotExist() throws Exception {
        comment("ravi", 2, "Buy milk").andExpect(status().isCreated());
        mvc.perform(get("/posts/2/comments").with(httpBasic("ravi", "ravi-demo-pass"))).andExpect(jsonPath("$[0].text").value("Buy milk"));
        mvc.perform(get("/posts/2/comments").with(httpBasic("asha", "asha-demo-pass"))).andExpect(status().isNotFound());
        mvc.perform(get("/posts/2/comments")).andExpect(status().isNotFound());
        comment("asha", 2, "Peeking").andExpect(status().isNotFound());
    }

    @Test
    void anAuthorFieldInTheBodyIsIgnored() throws Exception {
        mvc.perform(post("/posts/1/comments").with(httpBasic("ravi", "ravi-demo-pass")).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"text\":\"I am asha\",\"author\":\"asha\"}"))
                .andExpect(jsonPath("$.author").value("ravi"));
    }

    @ParameterizedTest
    @ValueSource(strings = {
            "<script>alert(1)</script>",
            "<SCRIPT>alert(1)</SCRIPT>",
            "<scr<script>ipt>alert(1)</script>",
            "<img src=x onerror=alert(1)>",
            "<svg onload=alert(1)>",
            "\"><iframe src=javascript:alert(1)>",
            "<a href=\"javascript:alert(1)\">win a prize</a>"})
    void everyPayloadIsStoredAsTextAndShownAsText(String payload) throws Exception {
        comment("ravi", 1, payload).andExpect(status().isCreated()).andExpect(jsonPath("$.text").value(payload));
        String shown = html(1).replaceAll("(?s).*<p>(.*)</p>.*", "$1"); // the user's text, as the page carries it
        assertThat(shown).isEqualTo(HtmlUtils.htmlEscape(payload)).doesNotContain("<").doesNotContain("\"");
    }

    @Test
    void aRefusedPayloadIsNotEchoedInTheError() throws Exception {
        comment("ravi", 1, "<script>steal()</script> you idiot")
                .andExpect(status().isUnprocessableContent())
                .andExpect(content().string(not(containsString("<script>"))));
    }
}
