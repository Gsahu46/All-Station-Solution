package com.mapwise.edge;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.util.Collection;

@RestController
class UploadController {

    private final Uploads uploads;

    UploadController(Uploads uploads) {
        this.uploads = uploads;
    }

    /** 201 with a Location for the new upload. */
    @PostMapping("/uploads")
    ResponseEntity<Uploads.Upload> upload(HttpServletRequest req, Authentication auth) throws IOException {
        Uploads.Upload saved = uploads.save(auth.getName(), req.getRemoteAddr(), req.getInputStream());
        // The link the client used: its Host header.
        return ResponseEntity.created(java.net.URI.create("http://" + req.getHeader("Host") + "/uploads/" + saved.id())).body(saved);
    }

    /** Another user's upload is a 404, the same as one that does not exist. */
    @GetMapping("/uploads/{id}")
    Uploads.Upload upload(@PathVariable long id, Authentication auth) {
        return uploads.find(auth.getName(), id).orElseThrow(() ->
                new ErrorResponseException(HttpStatus.NOT_FOUND, ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No such upload."), null));
    }

    /** Admins, from the office network only (see SecurityConfig). */
    @GetMapping("/admin/uploads")
    Collection<Uploads.Upload> all() {
        return uploads.all();
    }
}
