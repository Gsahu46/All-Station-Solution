package com.tijori.kyc;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Component;
import org.springframework.web.ErrorResponseException;

import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * Stores uploaded documents on disk under names the server makes up, never the client's. The bytes are streamed
 * from the request to the file in small pieces, counted and hashed on the way, and the first bytes decide the type.
 */
@Component
class DocumentStore {

    static final long MAX_BYTES = 5L * 1024 * 1024;

    record Document(String id, long customerId, String type, String fileName, String contentType, long sizeBytes, String sha256, Instant uploadedAt) {
    }

    /** A stored document, and whether this upload added it (false: the same bytes were already there). */
    record Stored(Document document, boolean isNew) {
    }

    /** Only these types are accepted, recognised by their first bytes ("magic numbers"), not by name or header. */
    private static final Map<String, byte[]> SIGNATURES = Map.of(
            "application/pdf", "%PDF-".getBytes(),
            "image/png", new byte[]{(byte) 0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A},
            "image/jpeg", new byte[]{(byte) 0xFF, (byte) 0xD8, (byte) 0xFF});

    private final Path root;
    // shortcut: the list of documents is kept in memory and lost on restart; a real service keeps it in a table.
    private final Map<Long, List<Document>> byCustomer = new ConcurrentHashMap<>();

    DocumentStore(@Value("${tijori.storage-dir}") Path root) throws IOException {
        this.root = Files.createDirectories(root).toRealPath();
    }

    Stored store(long customerId, String type, String clientFileName, InputStream body) throws IOException {
        BufferedInputStream in = new BufferedInputStream(body);
        String contentType = sniff(in);
        String id = UUID.randomUUID().toString();
        Path dir = Files.createDirectories(root.resolve(Long.toString(customerId)));
        Path file = dir.resolve(id);   // the server's name: nothing from the client reaches the path
        MessageDigest sha;
        try {
            sha = MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
        long size;
        try (InputStream digesting = new DigestInputStream(in, sha); OutputStream out = Files.newOutputStream(file)) {
            size = copyAtMost(digesting, out, MAX_BYTES);
        } catch (TooLarge e) {
            Files.deleteIfExists(file);
            throw problem(HttpStatus.CONTENT_TOO_LARGE, "A document can be at most 5 MB");
        }
        String hash = HexFormat.of().formatHex(sha.digest());
        // The hash is only known once the file is read: a repeat is noticed after streaming, and its copy removed.
        synchronized (this) {
            List<Document> docs = byCustomer.computeIfAbsent(customerId, c -> new CopyOnWriteArrayList<>());
            for (Document earlier : docs) {
                if (earlier.type().equals(type) && earlier.sha256().equals(hash)) {
                    Files.delete(file);
                    return new Stored(earlier, false);
                }
            }
            Document d = new Document(id, customerId, type, displayName(clientFileName), contentType, size, hash, Instant.now());
            docs.add(d);
            return new Stored(d, true);
        }
    }

    List<Document> list(long customerId) {
        return List.copyOf(byCustomer.getOrDefault(customerId, List.of()));
    }

    /** The document's file, if this customer has a document with this id; the id is matched, never used as a path. */
    java.util.Optional<Map.Entry<Document, Path>> find(long customerId, String documentId) {
        return list(customerId).stream().filter(d -> d.id().equals(documentId)).findFirst()
                .map(d -> Map.entry(d, root.resolve(Long.toString(customerId)).resolve(d.id())));
    }

    Path root() {
        return root;
    }

    /** For tests: forget all documents. */
    void clear() {
        byCustomer.clear();
    }

    /** Looks at the first bytes without consuming them. */
    static String sniff(BufferedInputStream in) throws IOException {
        in.mark(16);
        byte[] head = in.readNBytes(8);
        in.reset();
        if (head.length == 0) {
            throw problem(HttpStatus.BAD_REQUEST, "The file is empty");
        }
        return SIGNATURES.entrySet().stream()
                .filter(s -> head.length >= s.getValue().length && Arrays.equals(Arrays.copyOf(head, s.getValue().length), s.getValue()))
                .map(Map.Entry::getKey).findFirst()
                .orElseThrow(() -> problem(HttpStatus.UNSUPPORTED_MEDIA_TYPE, "Only PDF, PNG and JPEG documents are accepted"));
    }

    /** Copies in 8 KB pieces and stops as soon as the limit is passed, without reading the rest. */
    static long copyAtMost(InputStream in, OutputStream out, long limit) throws IOException {
        byte[] buffer = new byte[8192];
        long total = 0;
        for (int n; (n = in.read(buffer)) != -1; ) {
            total += n;
            if (total > limit) {
                throw new TooLarge();
            }
            out.write(buffer, 0, n);
        }
        return total;
    }

    /** The client's name is shown, never used as a path: the last part only, safe characters, at most 100. */
    static String displayName(String clientFileName) {
        if (clientFileName == null) {
            return "document";
        }
        String last = clientFileName.substring(Math.max(clientFileName.lastIndexOf('/'), clientFileName.lastIndexOf('\\')) + 1);
        String safe = last.replaceAll("[^A-Za-z0-9._-]", "_");
        safe = safe.replaceAll("^\\.+", "");   // no hidden or "..": a name is never a directory
        return safe.isEmpty() ? "document" : safe.substring(0, Math.min(100, safe.length()));
    }

    static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }

    static final class TooLarge extends RuntimeException {
    }
}
