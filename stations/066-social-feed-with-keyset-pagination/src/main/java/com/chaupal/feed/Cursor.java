package com.chaupal.feed;

import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Base64;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Where the last page stopped: the last post's time and id. Opaque to clients (base64url of "v1:micros:id"), so they
 * pass it back unchanged and the server can change its contents later. Not a secret: anyone can decode it.
 */
record Cursor(Instant createdAt, long id) {

    private static final Pattern FORMAT = Pattern.compile("v1:(-?\\d{1,18}):(\\d{1,18})");

    String encode() {
        long micros = ChronoUnit.MICROS.between(Instant.EPOCH, createdAt);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(("v1:" + micros + ":" + id).getBytes(StandardCharsets.US_ASCII));
    }

    static Cursor decode(String text) {
        try {
            Matcher m = FORMAT.matcher(new String(Base64.getUrlDecoder().decode(text), StandardCharsets.US_ASCII));
            if (m.matches()) {
                return new Cursor(Instant.EPOCH.plus(Long.parseLong(m.group(1)), ChronoUnit.MICROS), Long.parseLong(m.group(2)));
            }
        } catch (IllegalArgumentException e) {
            // not base64: answered below like any other bad cursor
        }
        throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Not a cursor from this feed; start again without one");
    }
}
