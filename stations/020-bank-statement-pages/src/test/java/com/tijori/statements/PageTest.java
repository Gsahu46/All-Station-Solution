package com.tijori.statements;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** The generic page and the statement order, without HTTP. */
class PageTest {

    static final List<Transaction> STATEMENT = Accounts.generate(4_000);

    @Test
    void walkingEveryPageSeesEachTransactionOnceInOrder() {
        for (int size : new int[]{1, 7, 37, 100}) {
            List<Transaction> seen = new ArrayList<>();
            Page<Transaction> page;
            int n = 0;
            do {
                page = Page.of(STATEMENT, n++, size);
                seen.addAll(page.items());
            } while (page.hasNext());
            assertThat(seen).as("size " + size).isEqualTo(STATEMENT);
            assertThat(n).isEqualTo(page.totalPages());
        }
    }

    @Test
    void transactionsInTheSameMinuteAreOrderedByIdNewestFirst() {
        for (int i = 1; i < STATEMENT.size(); i++) {
            Transaction before = STATEMENT.get(i - 1);
            Transaction after = STATEMENT.get(i);
            assertThat(before.postedAt()).isAfterOrEqualTo(after.postedAt());
            if (before.postedAt().equals(after.postedAt())) {
                assertThat(before.id()).isGreaterThan(after.id());
            }
        }
    }

    @Test
    void anEmptyListIsOneEmptyPageWithNoLastId() {
        Page<Transaction> page = Page.of(List.of(), 0, 20);
        assertThat(page.items()).isEmpty();
        assertThat(page.totalPages()).isZero();
        assertThat(page.hasNext()).isFalse();
        assertThat(page.lastId()).isNull();
    }

    @Test
    void theGenericPageWorksForAnyIdentifiedType() {
        record Note(long id, String text) implements Page.Identified {
        }
        Page<Note> page = Page.of(List.of(new Note(5, "a"), new Note(4, "b"), new Note(3, "c")), 0, 2);
        assertThat(page.items()).extracting(Note::text).containsExactly("a", "b");
        assertThat(page.lastId()).isEqualTo(4);
    }
}
