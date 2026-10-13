package com.chaupal.comments;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Posts and comments in memory. The rules: who can see a post, moderation, and the rate limit. */
@Service
class CommentService {

    private final Map<Long, Post> posts = Map.of(
            1L, new Post(1, "asha", "Best cutting chai in Pune?", false),
            2L, new Post(2, "ravi", "Notes to self", true));
    private final List<Comment> comments = new ArrayList<>();
    private final Moderation moderation;
    private final RateLimiter rateLimiter;

    CommentService(Moderation moderation, RateLimiter rateLimiter) {
        this.moderation = moderation;
        this.rateLimiter = rateLimiter;
    }

    /** The text is stored exactly as typed: no stripping of tags. Output encoding makes it safe (CommentHtml). */
    Comment add(String user, long postId, String text) {
        visiblePost(postId, user);
        if (moderation.breaksRules(text)) {
            throw new Exceptions.BreaksCommunityRules();
        }
        if (!rateLimiter.tryAcquire(user)) {
            throw new Exceptions.TooManyComments();
        }
        var c = new Comment(UUID.randomUUID(), postId, user, text, Instant.now().truncatedTo(ChronoUnit.MILLIS));
        synchronized (comments) {
            comments.add(c);
        }
        return c;
    }

    /** user is null for a reader who is not signed in. */
    List<Comment> list(long postId, String user) {
        visiblePost(postId, user);
        synchronized (comments) {
            return comments.stream().filter(c -> c.postId() == postId).toList();
        }
    }

    private Post visiblePost(long postId, String user) {
        Post p = posts.get(postId);
        if (p == null || !p.visibleTo(user)) {
            throw new Exceptions.PostNotFound();
        }
        return p;
    }

    /** For tests only. */
    void clear() {
        synchronized (comments) {
            comments.clear();
        }
    }
}
