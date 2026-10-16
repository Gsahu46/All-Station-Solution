package com.chaupal.feed;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessException;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules as PostgreSQL enforces them, with plain SQL; test rows start with "Test" and are removed afterwards. */
class PostDatabaseTest extends ApiTest {

    @AfterEach
    void removeTestRows() {
        jdbc.sql("DELETE FROM posts WHERE body LIKE 'Test%'").update();
        jdbc.sql("DELETE FROM authors WHERE id >= 100").update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO posts (author_id, body) VALUES (1, '   ')").update())
                .isInstanceOf(DataAccessException.class).hasMessageContaining("posts_body_not_blank");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO posts (author_id, body) VALUES (99, 'Test orphan')").update()).hasMessageContaining("posts_author_fk");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO authors (id, handle) VALUES (100, 'Asha Writes')").update()).hasMessageContaining("authors_handle_shape");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO authors (id, handle) VALUES (100, 'kabir')").update()).hasMessageContaining("authors_handle_unique");
    }

    @Test
    void aNewPostIsStampedByTheDatabaseAndTopsTheFeed() throws Exception {
        jdbc.sql("INSERT INTO posts (author_id, body) VALUES (2, 'Test hello Chaupal')").update();   // created_at = now(), after every demo post
        assertThat(getFeed(null, 1).get("posts").get(0).get("body").asString()).isEqualTo("Test hello Chaupal");
    }

    @Test
    void aNewAuthorWithAnOrphanPostIsNotAddedAtAll() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(tx -> {
            jdbc.sql("INSERT INTO authors (id, handle) VALUES (100, 'test_author')").update();
            jdbc.sql("INSERT INTO posts (author_id, body) VALUES (100, 'Test first post')").update();
            jdbc.sql("INSERT INTO posts (author_id, body) VALUES (101, 'Test wrong author')").update();
        })).hasMessageContaining("posts_author_fk");
        assertThat(jdbc.sql("SELECT count(*) FROM authors WHERE id = 100").query(Long.class).single()).isZero();
        assertThat(jdbc.sql("SELECT count(*) FROM posts WHERE body LIKE 'Test%'").query(Long.class).single()).isZero();
    }
}
