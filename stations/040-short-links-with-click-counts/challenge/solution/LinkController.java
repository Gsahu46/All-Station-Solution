package com.chhotu.links;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Future;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.time.OffsetDateTime;
import java.util.Locale;

/** Codes are case-sensitive on purpose: base62 uses upper and lower case as different digits, so they are never normalised. */
@RestController
class LinkController {

    record NewLink(@NotBlank @Size(max = 2048) String targetUrl,
                   @Pattern(regexp = "[0-9A-Za-z]{7}", message = "must be 7 letters or digits") String code,
                   @Future OffsetDateTime expiresAt) {
    }

    record Created(String code, String shortUrl, String targetUrl) {
    }

    record Stats(String code, String targetUrl, long clicks, OffsetDateTime createdAt) {
    }

    private final LinkStore links;
    private final ClickCounter clicks;
    private final String baseUrl;

    LinkController(LinkStore links, ClickCounter clicks, @Value("${chhotu.base-url}") String baseUrl) {
        this.links = links;
        this.clicks = clicks;
        this.baseUrl = baseUrl;
    }

    @PostMapping("/links")
    ResponseEntity<Created> create(@Valid @RequestBody NewLink request) {
        String target = request.targetUrl().strip();
        if (!isWebAddress(target)) {
            throw problem(HttpStatus.BAD_REQUEST, "Not a web address", "targetUrl must be an http or https address with a host.");
        }
        String code;
        if (request.code() != null) {
            if (!links.insert(request.code(), target, request.expiresAt())) {
                throw problem(HttpStatus.CONFLICT, "Code taken", "The short code " + request.code() + " is already in use.");
            }
            code = request.code();
        } else {
            code = links.create(target, request.expiresAt()).orElseThrow(() ->
                    problem(HttpStatus.SERVICE_UNAVAILABLE, "Try again", "Could not find a free short code; please try again."));
        }
        String shortUrl = baseUrl + "/" + code;
        return ResponseEntity.created(URI.create(shortUrl)).body(new Created(code, shortUrl, target));
    }

    /**
     * 302, not 301: browsers and proxies may cache a 301 forever, so later clicks would never reach us (no count) and
     * the destination could never be changed. The price is one request to us per click.
     */
    @GetMapping("/{code:[0-9A-Za-z]{7}}")
    ResponseEntity<Void> follow(@PathVariable String code) {
        LinkStore.Target target = links.target(code).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Link not found", "No short link " + code + "."));
        if (target.expired()) {
            throw problem(HttpStatus.GONE, "Link expired", "The short link " + code + " has expired.");
        }
        clicks.record(code);
        return ResponseEntity.status(HttpStatus.FOUND).location(URI.create(target.url())).build();
    }

    /** Stored clicks plus those not yet flushed by this instance. */
    @GetMapping("/links/{code}/stats")
    Stats stats(@PathVariable String code) {
        LinkStore.Link link = links.link(code).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "Link not found", "No short link " + code + "."));
        return new Stats(link.code(), link.targetUrl(), link.clicks() + clicks.pending(code), link.createdAt());
    }

    /** Only http and https with a host: never javascript:, data: or file:, which a short link would hide. */
    static boolean isWebAddress(String url) {
        try {
            URI uri = new URI(url);
            String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase(Locale.ROOT);
            return (scheme.equals("http") || scheme.equals("https")) && uri.getHost() != null;
        } catch (java.net.URISyntaxException e) {
            return false;
        }
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
