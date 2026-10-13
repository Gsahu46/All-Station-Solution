package com.chaupal.comments;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.security.Principal;
import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/posts/{postId}/comments")
class CommentController {

    private final CommentService service;

    CommentController(CommentService service) {
        this.service = service;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    Comment add(Principal user, @PathVariable long postId, @Valid @RequestBody CommentRequest request) {
        return service.add(user.getName(), postId, request.text());
    }

    /** Challenge 2. 204 every time, so a reporter cannot tell how many others reported. */
    @PostMapping("/{commentId}/reports")
    ResponseEntity<Void> report(Principal user, @PathVariable long postId, @PathVariable UUID commentId) {
        service.report(user.getName(), postId, commentId);
        return ResponseEntity.noContent().build();
    }

    /** JSON for the app. The text is raw: the app must put it on screen as text, never as HTML. */
    @GetMapping(produces = MediaType.APPLICATION_JSON_VALUE)
    List<Comment> list(Principal user, @PathVariable long postId) {
        return service.list(postId, user == null ? null : user.getName());
    }

    /** The same comments as an HTML fragment for the website, with every piece of user text encoded. */
    @GetMapping(produces = MediaType.TEXT_HTML_VALUE)
    String html(Principal user, @PathVariable long postId) {
        return CommentHtml.render(service.list(postId, user == null ? null : user.getName()));
    }
}
