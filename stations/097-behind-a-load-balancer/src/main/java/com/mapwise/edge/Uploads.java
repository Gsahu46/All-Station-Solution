package com.mapwise.edge;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Component;
import org.springframework.web.ErrorResponseException;

import java.io.IOException;
import java.io.InputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Collection;
import java.util.HexFormat;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Simulated storage: an upload is read to the end, counted and hashed; the bytes themselves are not kept.
 * shortcut: the records are in this server's memory, so another server behind the balancer does not know them
 * (that is what sticky sessions paper over); keep them in a database and the bytes in object storage.
 */
@Component
class Uploads {

    record Upload(long id, String owner, long bytes, String sha256, String clientIp) {
    }

    private final long maxBytes;
    private final Map<Long, Upload> uploads = new ConcurrentHashMap<>();
    private final AtomicLong ids = new AtomicLong();

    Uploads(@Value("${mapwise.max-upload-bytes}") long maxBytes) {
        this.maxBytes = maxBytes;
    }

    /** Streams the body in 8 KB pieces: memory stays flat and reading stops at the limit. */
    Upload save(String owner, String clientIp, InputStream body) throws IOException {
        MessageDigest sha256;
        try {
            sha256 = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
        long total = 0;
        byte[] buffer = new byte[8192];
        for (int n; (n = body.read(buffer)) != -1; ) {   // a stalled client: Tomcat's read timeout ends it with 408
            total += n;
            if (total > maxBytes) {
                throw tooLarge();
            }
            sha256.update(buffer, 0, n);
        }
        long id = ids.incrementAndGet();
        Upload upload = new Upload(id, owner, total, HexFormat.of().formatHex(sha256.digest()), clientIp);
        uploads.put(id, upload);
        return upload;
    }

    Optional<Upload> find(String owner, long id) {
        return Optional.ofNullable(uploads.get(id)).filter(u -> u.owner().equals(owner));
    }

    Collection<Upload> all() {
        return uploads.values();
    }

    private ErrorResponseException tooLarge() {
        return new ErrorResponseException(HttpStatus.CONTENT_TOO_LARGE,
                ProblemDetail.forStatusAndDetail(HttpStatus.CONTENT_TOO_LARGE, "Uploads are limited to " + maxBytes + " bytes."), null);
    }
}
