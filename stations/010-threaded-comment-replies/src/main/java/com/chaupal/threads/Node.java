package com.chaupal.threads;

import java.time.Instant;
import java.util.List;

/**
 * One comment in the tree, with its replies nested inside. At the depth limit, replies is empty and
 * moreReplies says how many are hidden below, so the app can show "Continue this thread (n)".
 */
public record Node(long id, String author, String text, Instant createdAt, List<Node> replies, int moreReplies) {
}
