package com.chhotu.links;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The table's rules with Java bypassed, collisions, and a rollback. */
class LinkDatabaseTest extends ApiTest {

    @MockitoBean
    CodeGenerator codes;
    @Autowired
    TransactionTemplate transaction;

    void insert(String code, String url) {
        jdbc.sql("INSERT INTO links (code, target_url) VALUES (?, ?)").params(code, url).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        insert("abcDEF1", "https://example.com");
        assertThatThrownBy(() -> insert("abcDEF1", "https://example.org")).hasMessageContaining("links_pkey");
        assertThatThrownBy(() -> insert("abc-EF1", "https://example.com")).hasMessageContaining("links_code_base62");
        assertThatThrownBy(() -> insert("abcDEF2", "javascript:alert(1)")).hasMessageContaining("links_target_web");
        assertThatThrownBy(() -> jdbc.sql("UPDATE links SET clicks = -1").update()).hasMessageContaining("links_clicks_non_negative");
    }

    @Test
    void codesDifferingOnlyInCaseAreDifferentLinks() {
        insert("abcDEF1", "https://example.com/upper");
        insert("abcdef1", "https://example.com/lower");
        assertThat(targetOf("abcDEF1")).endsWith("upper");
        assertThat(targetOf("abcdef1")).endsWith("lower");
    }

    @Test
    void whenEveryAttemptCollidesNothingIsOverwrittenAndTheAnswerIs503() throws Exception {
        when(codes.next()).thenReturn("Taken01");
        insert("Taken01", "https://example.com/original");
        create("https://example.com/newcomer").andExpect(status().isServiceUnavailable()).andExpect(jsonPath("$.title").value("Try again"));
        assertThat(targetOf("Taken01")).endsWith("original");
    }

    @Test
    void aFailedInsertInATransactionTakesTheEarlierOneWithIt() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(status -> {
            insert("First01", "https://example.com/one");
            insert("Second2", "ftp://example.com/two");   // refused by links_target_web
        })).hasMessageContaining("links_target_web");
        assertThat(jdbc.sql("SELECT count(*) FROM links").query(Long.class).single()).isZero();
    }
}
