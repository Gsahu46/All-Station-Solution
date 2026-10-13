package com.chaupal.threads;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
class CommentTreeController {

    record CommentTree(long postId, int maxDepth, List<Node> comments) {
    }

    private final CommentStore store;

    CommentTreeController(CommentStore store) {
        this.store = store;
    }

    /** maxDepth is capped at 10: deep enough for any conversation, shallow enough for any phone and any JSON parser. */
    @GetMapping("/posts/{postId}/comment-tree")
    CommentTree tree(@PathVariable long postId, @RequestParam(defaultValue = "5") @Min(1) @Max(10) int maxDepth) {
        List<Comment> comments = store.forPost(postId).orElseThrow(() -> {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No post has this id.");
            p.setTitle("Post not found");
            return new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
        });
        return new CommentTree(postId, maxDepth, ThreadBuilder.build(comments, maxDepth));
    }
}
