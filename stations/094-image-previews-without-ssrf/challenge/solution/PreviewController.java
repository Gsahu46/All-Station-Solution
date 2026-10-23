package com.chaupal.previews;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.net.URISyntaxException;

@RestController
class PreviewController {

    record PreviewRequest(@NotNull @Size(max = 2000) String url) {
    }

    private final Previews previews;

    PreviewController(Previews previews) {
        this.previews = previews;
    }

    @PostMapping("/link-previews")
    @ResponseStatus(HttpStatus.CREATED)
    Previews.Preview create(@Valid @RequestBody PreviewRequest body, Authentication who) {
        URI uri;
        try {
            uri = new URI(body.url().strip());
        } catch (URISyntaxException e) {
            throw SafeFetcher.problem(HttpStatus.BAD_REQUEST, "Not a valid link");
        }
        return previews.create(who.getName(), uri);
    }

    /** The image, through the server: members' apps never contact the site, and the server fetches it with every check. */
    @GetMapping("/link-previews/{id}/image")
    org.springframework.http.ResponseEntity<byte[]> image(@PathVariable String id, Authentication who) {
        SafeFetcher.Fetched f = previews.image(who.getName(), id);
        return org.springframework.http.ResponseEntity.ok().contentType(org.springframework.http.MediaType.parseMediaType(f.mimeType())).body(f.head());
    }

    @GetMapping("/link-previews/{id}")
    Previews.Preview get(@PathVariable String id, Authentication who) {
        return previews.get(who.getName(), id);
    }
}
