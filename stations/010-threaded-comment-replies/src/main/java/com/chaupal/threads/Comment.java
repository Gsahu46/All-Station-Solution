package com.chaupal.threads;

import java.time.Instant;

/** A comment as it is stored: flat, with the id of the comment it replies to (null for a top-level comment). */
record Comment(long id, long postId, Long parentId, String author, String text, Instant createdAt) {
}
