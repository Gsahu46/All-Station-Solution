package com.chaupal.feed;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

/**
 * Challenge 2: every page also carries "topCursor", the position of its first post. GET /feed/new?cursor=<topCursor>
 * returns the posts made since, newest first (at most limit), with its own topCursor, for pull-to-refresh.
 */
class PullToRefreshChallengeTest extends ApiTest {

    @AfterEach
    void removeNewPosts() {
        jdbc.sql("DELETE FROM posts WHERE body LIKE 'Test new post%'").update();
    }

    @Test
    void onlyThePostsMadeSince() throws Exception {
        JsonNode page = getFeed(null, 20);
        for (int i = 1; i <= 3; i++) {
            post("Test new post " + i);
        }
        JsonNode fresh = json.readTree(mvc.perform(get("/feed/new").param("cursor", page.get("topCursor").asString())).andReturn().getResponse().getContentAsString());
        assertThat(fresh.get("posts").findValuesAsString("body")).containsExactly("Test new post 3", "Test new post 2", "Test new post 1");
        JsonNode again = json.readTree(mvc.perform(get("/feed/new").param("cursor", fresh.get("topCursor").asString())).andReturn().getResponse().getContentAsString());
        assertThat(again.get("posts")).isEmpty();
    }
}
