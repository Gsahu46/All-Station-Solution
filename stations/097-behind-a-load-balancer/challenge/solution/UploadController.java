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
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

import java.io.IOException;
import java.util.Collection;

@RestController
class UploadController {

    private final Uploads uploads;
    private final UploadLimiter limiter;

    UploadController(Uploads uploads, UploadLimiter limiter) {
        this.uploads = uploads;
        this.limiter = limiter;
    }

    /** 201 with a Location built from the request: https://maps.mapwise.example/... behind the balancer, not http://10.0.0.17:8080/... */
    @PostMapping("/uploads")
    ResponseEntity<Uploads.Upload> upload(HttpServletRequest req, Authentication auth) throws IOException {
        long wait = limiter.take(req.getRemoteAddr());   // challenge 2: the real client, thanks to the valve
        if (wait > 0) {
            ErrorResponseException refused = new ErrorResponseException(HttpStatus.TOO_MANY_REQUESTS,
                    ProblemDetail.forStatusAndDetail(HttpStatus.TOO_MANY_REQUESTS, "At most " + UploadLimiter.PER_MINUTE + " uploads a minute from one address."), null);
            refused.getHeaders().set("Retry-After", Long.toString(wait));
            throw refused;
        }
        Uploads.Upload saved = uploads.save(auth.getName(), req.getRemoteAddr(), req.getInputStream());
        return ResponseEntity.created(ServletUriComponentsBuilder.fromCurrentContextPath().path("/uploads/{id}").build(saved.id())).body(saved);
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
