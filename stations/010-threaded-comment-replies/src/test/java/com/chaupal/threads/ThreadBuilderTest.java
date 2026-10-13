package com.chaupal.threads;

import org.junit.jupiter.api.Test;

import java.time.Duration;
import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertTimeoutPreemptively;

/** The builder on its own: broken data, ordering, and very deep or very wide threads. */
class ThreadBuilderTest {

    private static final Instant T = Instant.parse("2026-10-12T04:30:00Z");

    private static Comment c(long id, Long parent, int second) {
        return new Comment(id, 1, parent, "u" + id, "text " + id, T.plusSeconds(second));
    }

    @Test
    void aReplyWhoseParentIsGoneIsShownAtTheTop() {
        var tree = ThreadBuilder.build(List.of(c(1, null, 0), c(2, 99L, 1)), 5);
        assertThat(tree).extracting(Node::id).containsExactly(1L, 2L);
    }

    @Test
    void commentsInALoopDoNotHangTheBuilder() {
        // Corrupt data: 2 replies to 3, 3 replies to 2, 4 replies to itself. None has a top-level ancestor.
        var comments = List.of(c(1, null, 0), c(2, 3L, 1), c(3, 2L, 2), c(4, 4L, 3));
        var tree = assertTimeoutPreemptively(Duration.ofSeconds(2), () -> ThreadBuilder.build(comments, 10));
        assertThat(tree).extracting(Node::id).containsExactly(1L);
    }

    @Test
    void siblingsAreOldestFirstThenById() {
        var tree = ThreadBuilder.build(List.of(c(5, null, 9), c(3, null, 1), c(4, null, 1), c(2, null, 5)), 1);
        assertThat(tree).extracting(Node::id).containsExactly(3L, 4L, 2L, 5L);
    }

    @Test
    void countingBelowAHundredThousandLevelsUsesNoRecursion() {
        var chain = new java.util.ArrayList<Comment>();
        for (int i = 0; i < 100_000; i++) {
            chain.add(c(i + 1, i == 0 ? null : (long) i, i));
        }
        var tree = ThreadBuilder.build(chain, 1);
        assertThat(tree.getFirst().moreReplies()).isEqualTo(99_999);
    }

    @Test
    void aWideThreadKeepsEveryReply() {
        var wide = new java.util.ArrayList<Comment>(List.of(c(1, null, 0)));
        for (int i = 2; i <= 5_000; i++) {
            wide.add(c(i, 1L, i));
        }
        assertThat(ThreadBuilder.build(wide, 2).getFirst().replies()).hasSize(4_999);
    }
}
