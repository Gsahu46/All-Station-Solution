package com.chaupal.comments;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.not;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.httpBasic;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** HTTP contract: post, list as JSON or HTML, and every way a comment can be refused. */
class CommentContractTest extends ApiTest {

    @Test
    void aCommentIs201WithTheSignedInUserAsAuthor() throws Exception {
        comment("ravi", 1, "Amruttulya near FC Road, every time.")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").isNotEmpty())
                .andExpect(jsonPath("$.postId").value(1))
                .andExpect(jsonPath("$.author").value("ravi"))
                .andExpect(jsonPath("$.text").value("Amruttulya near FC Road, every time."));
    }

    @Test
    void jsonListsCommentsOldestFirstWithTheTextExactlyAsTyped() throws Exception {
        comment("ravi", 1, "First!");
        comment("asha", 1, "Use <b> for bold? & \"quotes\"");
        mvc.perform(get("/posts/1/comments"))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$[*].author", contains("ravi", "asha")))
                .andExpect(jsonPath("$[1].text").value("Use <b> for bold? & \"quotes\""));
    }

    @Test
    void theHtmlFragmentEncodesEveryCharacterThatMatters() throws Exception {
        comment("asha", 1, "Use <b> for bold? & \"quotes\" 'too'");
        String page = mvc.perform(get("/posts/1/comments").accept(MediaType.TEXT_HTML))
                .andExpect(status().isOk())
                .andExpect(content().contentTypeCompatibleWith(MediaType.TEXT_HTML))
                .andExpect(header().string("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"))
                .andReturn().getResponse().getContentAsString();
        assertThat(page).contains("<p>Use &lt;b&gt; for bold? &amp; &quot;quotes&quot; &#39;too&#39;</p>");
    }

    @Test
    void blankOrTooLongTextIs400() throws Exception {
        comment("asha", 1, "   ").andExpect(status().isBadRequest()).andExpect(jsonPath("$.errors.text").value("must not be blank"));
        comment("asha", 1, "a".repeat(501)).andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.text").value("must be at most 500 characters"));
        comment("asha", 1, "a".repeat(500)).andExpect(status().isCreated());
    }

    @Test
    void aBannedWordIs422WithoutRepeatingIt() throws Exception {
        comment("ravi", 1, "What an 1d10t")
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.type").value("https://chaupal.example/problems/community-rules"))
                .andExpect(content().string(not(containsString("1d10t"))));
        mvc.perform(get("/posts/1/comments")).andExpect(jsonPath("$").isEmpty());
    }

    @Test
    void theSixthCommentInAMinuteIs429WithRetryAfter() throws Exception {
        for (int i = 1; i <= 5; i++) {
            comment("kabir", 1, "Comment " + i).andExpect(status().isCreated());
        }
        comment("kabir", 1, "Comment 6")
                .andExpect(status().isTooManyRequests())
                .andExpect(header().string("Retry-After", "60"))
                .andExpect(jsonPath("$.type").value("https://chaupal.example/problems/too-many-comments"));
        comment("asha", 1, "My first today").andExpect(status().isCreated()); // the limit is per user
    }

    @Test
    void anUnknownPostIs404() throws Exception {
        comment("asha", 99, "Hello").andExpect(status().isNotFound());
        mvc.perform(get("/posts/99/comments")).andExpect(status().isNotFound())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
    }

    @Test
    void brokenJsonIs400() throws Exception {
        mvc.perform(post("/posts/1/comments").with(httpBasic("asha", "asha-demo-pass"))
                        .contentType(MediaType.APPLICATION_JSON).content("{\"text\":"))
                .andExpect(status().isBadRequest())
                .andExpect(content().contentType(MediaType.APPLICATION_PROBLEM_JSON));
    }
}
