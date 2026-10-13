package com.chaupal.threads;

import java.time.Instant;
import java.util.List;

/**
 * Challenge 1 adds totalReplies: every reply below this comment, at any depth, shown or not.
 * The six-argument constructor keeps older code (and the station's tests) compiling.
 */
public record Node(long id, String author, String text, Instant createdAt, List<Node> replies, int moreReplies, int totalReplies) {

    public Node(long id, String author, String text, Instant createdAt, List<Node> replies, int moreReplies) {
        this(id, author, text, createdAt, replies, moreReplies, 0);
    }
}
