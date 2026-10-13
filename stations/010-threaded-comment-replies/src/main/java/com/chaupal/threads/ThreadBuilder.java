package com.chaupal.threads;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Builds the reply tree from a flat list, in two passes and without unbounded recursion:
 * 1. one pass over the list groups comments by parent id in a map (each lookup is O(1), no searching);
 * 2. nodes are built from the top-level comments down, at most maxDepth levels; below that, replies are
 *    only counted, with an explicit stack instead of recursion, so a 100,000-deep thread cannot overflow.
 */
final class ThreadBuilder {

    /** Oldest first; two comments with the same time are ordered by id, so the order never changes between requests. */
    static final Comparator<Comment> ORDER = Comparator.comparing(Comment::createdAt).thenComparingLong(Comment::id);

    private ThreadBuilder() {
    }

    static List<Node> build(List<Comment> comments, int maxDepth) {
        Set<Long> ids = new HashSet<>();
        comments.forEach(c -> ids.add(c.id()));
        Map<Long, List<Comment>> children = new HashMap<>();
        List<Comment> roots = new ArrayList<>();
        for (Comment c : comments) {
            // A reply whose parent is missing (deleted, or never existed) is shown at the top, not lost.
            if (c.parentId() == null || !ids.contains(c.parentId())) {
                roots.add(c);
            } else {
                children.computeIfAbsent(c.parentId(), k -> new ArrayList<>()).add(c);
            }
        }
        // Comments in a loop (A replies to B, B replies to A) have no top-level ancestor, so they are never reached.
        roots.sort(ORDER);
        children.values().forEach(list -> list.sort(ORDER));
        return roots.stream().map(r -> node(r, 1, maxDepth, children)).toList();
    }

    /** Recursion here is safe: it goes at most maxDepth levels deep, and maxDepth is capped at 10. */
    private static Node node(Comment c, int depth, int maxDepth, Map<Long, List<Comment>> children) {
        List<Comment> replies = children.getOrDefault(c.id(), List.of());
        if (depth == maxDepth) {
            return new Node(c.id(), c.author(), c.text(), c.createdAt(), List.of(), countBelow(c.id(), children));
        }
        List<Node> nested = replies.stream().map(r -> node(r, depth + 1, maxDepth, children)).toList();
        return new Node(c.id(), c.author(), c.text(), c.createdAt(), nested, 0);
    }

    /** All replies below a comment, at any depth, counted with a stack instead of recursion. */
    static int countBelow(long id, Map<Long, List<Comment>> children) {
        int count = 0;
        Set<Long> seen = new HashSet<>(List.of(id)); // corrupt data can loop (A replies to B, B to A): count each comment once
        Deque<Long> todo = new ArrayDeque<>(List.of(id));
        while (!todo.isEmpty()) {
            for (Comment reply : children.getOrDefault(todo.pop(), List.of())) {
                if (seen.add(reply.id())) {
                    count++;
                    todo.push(reply.id());
                }
            }
        }
        return count;
    }
}
