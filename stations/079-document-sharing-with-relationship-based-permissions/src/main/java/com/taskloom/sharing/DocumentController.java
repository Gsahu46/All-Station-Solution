package com.taskloom.sharing;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
class DocumentController {

    record Share(@NotNull @Pattern(regexp = "(user|team):[a-z0-9.-]{1,40}") String subject, @NotNull @Pattern(regexp = "viewer|editor") String relation) {
    }

    private final Documents documents;
    private final Permissions permissions;

    DocumentController(Documents documents, Permissions permissions) {
        this.documents = documents;
        this.permissions = permissions;
    }

    @GetMapping("/docs/{id}")
    Documents.Doc open(Authentication me, @PathVariable String id) {
        return documents.open(me.getName(), id);
    }

    @PostMapping("/docs/{id}/shares")
    @ResponseStatus(HttpStatus.CREATED)
    Share share(Authentication me, @PathVariable String id, @Valid @RequestBody Share body) {
        documents.share(me.getName(), id, body.subject(), body.relation());
        return body;
    }

    @GetMapping("/me/shared-with-me")
    List<Permissions.Shared> sharedWithMe(Authentication me) {
        return permissions.sharedWith(me.getName());
    }
}
