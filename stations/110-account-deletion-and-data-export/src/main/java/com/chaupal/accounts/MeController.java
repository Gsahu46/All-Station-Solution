package com.chaupal.accounts;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;

/** The person's own data: "me" is always the signed-in account, never an id in the request. */
@RestController
class MeController {

    private final Accounts accounts;

    MeController(Accounts accounts) {
        this.accounts = accounts;
    }

    @PostMapping("/me/data-export")
    ResponseEntity<Accounts.Export> requestExport(Authentication me) {
        Accounts.Export e = accounts.requestExport(accounts.idOf(me.getName()));
        return ResponseEntity.accepted().location(URI.create("/me/data-exports/" + e.id())).body(e);
    }

    @GetMapping("/me/data-exports/{id}")
    Accounts.Export export(Authentication me, @PathVariable long id) {
        return accounts.export(accounts.idOf(me.getName()), id).orElseThrow(() -> new ErrorResponseException(HttpStatus.NOT_FOUND));
    }

    @GetMapping("/me/data-exports/{id}/file")
    ResponseEntity<String> exportFile(Authentication me, @PathVariable long id) {
        long user = accounts.idOf(me.getName());
        accounts.export(user, id).orElseThrow(() -> new ErrorResponseException(HttpStatus.NOT_FOUND));
        String content = accounts.exportFile(user, id).orElseThrow(() -> new ErrorResponseException(HttpStatus.CONFLICT,
                ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, "The export is not ready yet."), null));
        return ResponseEntity.ok().contentType(MediaType.APPLICATION_JSON)
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"chaupal-data-" + id + ".json\"").body(content);
    }

    /** 202: the account is closed now; the erasure job removes the data shortly after, and within 90 days at most. */
    @DeleteMapping("/me")
    ResponseEntity<Accounts.Deletion> delete(Authentication me) {
        return ResponseEntity.accepted().body(accounts.requestDeletion(accounts.idOf(me.getName())));
    }
}
