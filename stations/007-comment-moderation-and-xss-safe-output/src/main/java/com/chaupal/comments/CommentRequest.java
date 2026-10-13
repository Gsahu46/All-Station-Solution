package com.chaupal.comments;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/** Body of POST /posts/{id}/comments. No author field: the author is the signed-in user. */
public record CommentRequest(@NotBlank @Size(max = 500, message = "must be at most 500 characters") String text) {

    public CommentRequest {
        text = text == null ? null : text.strip();
    }
}
