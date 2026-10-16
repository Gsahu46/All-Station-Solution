package com.chaupal.feed;

import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.empty;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.nullValue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class FeedContractTest extends ApiTest {

    @Test
    void theFirstPageIsTheNewestPosts() throws Exception {
        mvc.perform(get("/feed")).andExpect(status().isOk())
                .andExpect(jsonPath("$.posts", hasSize(20)))
                .andExpect(jsonPath("$.posts[0].id").value(100000)).andExpect(jsonPath("$.posts[0].author").value("asha_writes"))
                .andExpect(jsonPath("$.posts[0].body").value("Post number 100000")).andExpect(jsonPath("$.posts[0].createdAt").value("2026-10-01T05:33:20Z"))
                .andExpect(jsonPath("$.posts[19].id").value(99981)).andExpect(jsonPath("$.nextCursor").isString());
    }

    @Test
    void theCursorContinuesExactlyWhereThePageStopped() throws Exception {
        JsonNode first = getFeed(null, 7);
        JsonNode second = getFeed(first.get("nextCursor").asString(), 7);
        assertThat(first.get("posts").get(6).get("id").asLong()).isEqualTo(99994);
        assertThat(second.get("posts").get(0).get("id").asLong()).isEqualTo(99993);   // same second as 99994: the id breaks the tie
    }

    @Test
    void walkingTheLastThousandPostsShowsEachOnceAndEndsWithNoCursor() throws Exception {
        Set<Long> seen = new HashSet<>();
        String cursor = getFeed(null, 50).get("nextCursor").asString();
        for (int page = 0; page < 19; page++) {
            JsonNode next = getFeed(cursor, 50);
            next.get("posts").forEach(p -> seen.add(p.get("id").asLong()));
            cursor = next.get("nextCursor").asString();
        }
        assertThat(seen).hasSize(950);
        JsonNode nearEnd = json.readTree(mvc.perform(get("/feed").param("limit", "50").param("cursor", new Cursor(java.time.Instant.parse("2026-10-01T00:00:01Z"), 6).encode()))
                .andReturn().getResponse().getContentAsString());
        assertThat(nearEnd.get("posts")).hasSize(5);   // posts 1 to 5, the oldest
        assertThat(nearEnd.get("nextCursor").isNull()).isTrue();
    }

    @Test
    void aCursorPastTheOldestPostIsAnEmptyPage() throws Exception {
        mvc.perform(get("/feed").param("cursor", new Cursor(java.time.Instant.parse("2026-01-01T00:00:00Z"), 1).encode())).andExpect(status().isOk())
                .andExpect(jsonPath("$.posts", empty())).andExpect(jsonPath("$.nextCursor", nullValue()));
    }

    @Test
    void aCursorThatIsNotOursOrABadLimitIs400() throws Exception {
        mvc.perform(get("/feed").param("cursor", "not-a-cursor!")).andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").value("Not a cursor from this feed; start again without one"));
        mvc.perform(get("/feed").param("cursor", "djE6MTIzOmFiYw")).andExpect(status().isBadRequest());   // base64 of "v1:123:abc"
        mvc.perform(get("/feed").param("cursor", "MTIzNDU2")).andExpect(status().isBadRequest());         // base64 of "123456": an old offset
        mvc.perform(get("/feed").param("limit", "0")).andExpect(status().isBadRequest());
        mvc.perform(get("/feed").param("limit", "51")).andExpect(status().isBadRequest());
    }
}
