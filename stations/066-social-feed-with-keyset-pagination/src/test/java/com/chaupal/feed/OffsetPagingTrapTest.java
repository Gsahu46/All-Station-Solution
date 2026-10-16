package com.chaupal.feed;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.JsonNode;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

/** Written first. The old OFFSET feed and a time-only cursor, against the keyset feed, on the same 100,000 posts. */
class OffsetPagingTrapTest extends ApiTest {

    static final String OFFSET_PAGE = Feed.FIRST.replace("LIMIT :n", "LIMIT :n OFFSET :skip");

    @AfterEach
    void removeNewPosts() {
        jdbc.sql("DELETE FROM posts WHERE body LIKE 'Test new post%'").update();
    }

    private List<Long> offsetPage(int page, int size) {
        return jdbc.sql(OFFSET_PAGE).param("n", size).param("skip", page * size).query((rs, i) -> rs.getLong("id")).list();
    }

    private static List<Long> ids(JsonNode page) {
        List<Long> ids = new ArrayList<>();
        page.get("posts").forEach(p -> ids.add(p.get("id").asLong()));
        return ids;
    }

    @Test
    void page2000ByOffsetReadsEveryPostBeforeIt() {
        // Page 2,000 of 20: the old feed reads and throws away 40,000 posts (and their authors) to return 20.
        long offset = rowsRead(OFFSET_PAGE, Map.of("n", 20, "skip", 40_000));
        // The same page by keyset: start after post 60,001, the last one on page 1,999.
        Instant at = jdbc.sql("SELECT created_at FROM posts WHERE id = 60001").query(OffsetDateTime.class).single().toInstant();
        long keyset = rowsRead(Feed.AFTER, Map.of("n", 21, "createdAt", OffsetDateTime.ofInstant(at, ZoneOffset.UTC), "id", 60001L));
        assertThat(offset).isGreaterThanOrEqualTo(40_020);
        assertThat(keyset).isLessThanOrEqualTo(100);
    }

    @Test
    void newPostsPushRepeatsOntoTheNextOffsetPage() throws Exception {
        List<Long> page1 = offsetPage(0, 20);
        JsonNode keysetPage1 = getFeed(null, 20);
        for (int i = 1; i <= 3; i++) {
            post("Test new post " + i);   // three people post while the reader looks at page 1
        }
        List<Long> page2 = offsetPage(1, 20);
        assertThat(page2.subList(0, 3)).isEqualTo(page1.subList(17, 20));   // the last three of page 1, again

        List<Long> keysetPage2 = ids(getFeed(keysetPage1.get("nextCursor").asString(), 20));
        assertThat(keysetPage2).doesNotContainAnyElementsOf(ids(keysetPage1));
        assertThat(keysetPage2.getFirst()).isEqualTo(99980);   // straight on from 99981, new posts or not
    }

    @Test
    void aCursorWithTheTimeAloneSkipsPostsFromTheSameSecond() throws Exception {
        JsonNode first = getFeed(null, 7);   // ends at post 99994; posts 99990 to 99993 share its second
        Instant last = Instant.parse(first.get("posts").get(6).get("createdAt").asString());
        List<Long> timeOnly = jdbc.sql(Feed.FIRST.replace("ORDER BY", "WHERE p.created_at < :createdAt ORDER BY"))
                .param("createdAt", OffsetDateTime.ofInstant(last, ZoneOffset.UTC)).param("n", 7).query((rs, i) -> rs.getLong("id")).list();
        assertThat(timeOnly.getFirst()).isEqualTo(99989);   // 99990 to 99993 never shown
        assertThat(ids(getFeed(first.get("nextCursor").asString(), 7))).startsWith(99993L, 99992L, 99991L, 99990L, 99989L);
    }
}
