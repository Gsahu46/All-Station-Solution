package com.chaupal.comments;

import java.time.Instant;
import java.util.UUID;

/** A comment, stored exactly as typed. Making it safe is the job of whoever outputs it, for the format they output. */
public record Comment(UUID id, long postId, String author, String text, Instant createdAt) {
}
