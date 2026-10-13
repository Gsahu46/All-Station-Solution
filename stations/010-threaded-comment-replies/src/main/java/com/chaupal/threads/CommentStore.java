package com.chaupal.threads;

import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Comments per post, flat, in memory. Post 1 is a normal discussion, stored newest first on purpose: the builder
 * must sort, not trust storage order. Post 2 is one reply chain 100,000 deep (a bot replying to itself), the
 * thread that crashed the old code. Post 3 has no comments.
 */
@Component
class CommentStore {

    static final int DEEP_THREAD = 100_000;
    private static final Instant T0 = Instant.parse("2026-10-12T04:30:00Z");
    private final Map<Long, List<Comment>> byPost;

    CommentStore() {
        List<Comment> chai = List.of(
                c(9, 6L, "asha", "Not yet!", 9),
                c(8, 5L, "tara", "Closed on Mondays though.", 8),
                c(7, 3L, "kabir", "And cheaper.", 7),
                c(6, null, "meera", "Anyone tried the new place in Baner?", 6),
                c(5, 4L, "ravi", "Yes, opposite the gate.", 5),
                c(4, 2L, "asha", "The one near the college?", 4),
                c(3, 1L, "kabir", "Yewale is better.", 2),
                c(2, 1L, "ravi", "Amruttulya, every time.", 2),
                c(1, null, "asha", "Best cutting chai near FC Road?", 0));
        List<Comment> chain = new ArrayList<>(DEEP_THREAD);
        for (int i = 0; i < DEEP_THREAD; i++) {
            long id = 200_001L + i;
            chain.add(new Comment(id, 2, i == 0 ? null : id - 1, "echo-bot", "Reply " + i, T0.plusSeconds(i)));
        }
        byPost = Map.of(1L, chai, 2L, List.copyOf(chain), 3L, List.of());
    }

    private static Comment c(long id, Long parentId, String author, String text, int minutes) {
        return new Comment(id, 1, parentId, author, text, T0.plusSeconds(60L * minutes));
    }

    Optional<List<Comment>> forPost(long postId) {
        return Optional.ofNullable(byPost.get(postId));
    }
}
