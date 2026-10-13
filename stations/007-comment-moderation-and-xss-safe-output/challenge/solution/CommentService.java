package com.chaupal.comments;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/** Posts and comments in memory. The rules: who can see a post, moderation, and the rate limit. */
@Service
class CommentService {

    private final Map<Long, Post> posts = Map.of(
            1L, new Post(1, "asha", "Best cutting chai in Pune?", false),
            2L, new Post(2, "ravi", "Notes to self", true));
    private final List<Comment> comments = new ArrayList<>();
    /** Challenge 2: comment id -> who reported it. A Set, so the same reporter counts once. */
    private final Map<UUID, Set<String>> reports = new ConcurrentHashMap<>();
    static final int HIDE_AFTER = 3;
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
            return comments.stream().filter(c -> c.postId() == postId)
                    .filter(c -> reports.getOrDefault(c.id(), Set.of()).size() < HIDE_AFTER)
                    .toList();
        }
    }

    /** Challenge 2. The comment must be on a post this user can see; otherwise 404, as everywhere else. */
    void report(String user, long postId, UUID commentId) {
        visiblePost(postId, user);
        boolean exists;
        synchronized (comments) {
            exists = comments.stream().anyMatch(c -> c.id().equals(commentId) && c.postId() == postId);
        }
        if (!exists) {
            throw new Exceptions.PostNotFound();
        }
        reports.computeIfAbsent(commentId, id -> ConcurrentHashMap.newKeySet()).add(user);
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
        reports.clear();
    }
}
