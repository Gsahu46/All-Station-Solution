package com.chaupal.feed;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: GET /feed?author=kabir is one author's posts, newest first, with the same keyset cursor. An author
 * Chaupal does not know is 404.
 */
class AuthorFeedChallengeTest extends ApiTest {

    @Test
    void oneAuthorsPostsPageByPage() throws Exception {
        JsonNode first = json.readTree(mvc.perform(get("/feed").param("author", "kabir").param("limit", "3")).andReturn().getResponse().getContentAsString());
        assertThat(first.get("posts").findValuesAsString("author")).containsOnly("kabir");
        assertThat(first.get("posts").findValues("id")).extracting(JsonNode::asLong).containsExactly(99997L, 99993L, 99989L);
        JsonNode second = json.readTree(mvc.perform(get("/feed").param("author", "kabir").param("limit", "3").param("cursor", first.get("nextCursor").asString()))
                .andReturn().getResponse().getContentAsString());
        assertThat(second.get("posts").findValues("id")).extracting(JsonNode::asLong).containsExactly(99985L, 99981L, 99977L);
    }

    @Test
    void anUnknownAuthorIs404() throws Exception {
        mvc.perform(get("/feed").param("author", "nobody_here")).andExpect(status().isNotFound());
    }
}
