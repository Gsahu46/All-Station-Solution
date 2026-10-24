package com.mediqo.reports;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.FileAlreadyExistsException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * The reports on disk, standing in for object storage: a marker when a render is requested, the PDF when it is done,
 * a note when it failed for good. Files survive a restart, unlike memory. Simulated lab: report LR-n has n pages
 * (LR-0001 to LR-0500).
 * shortcut: one directory on one machine; use object storage (and a table for the state) with several servers.
 */
@Component
class LabReports {

    enum Status { QUEUED, READY, FAILED }

    static final Pattern ID = Pattern.compile("LR-(\\d{4})");
    private final Path dir;

    LabReports(@Value("${mediqo.reports.dir}") Path dir) throws IOException {
        this.dir = Files.createDirectories(dir);
    }

    /** Pages of a known report; empty for one the lab does not have. */
    Optional<Integer> pages(String id) {
        Matcher m = ID.matcher(id);
        if (!m.matches()) {
            return Optional.empty();
        }
        int n = Integer.parseInt(m.group(1));
        return n >= 1 && n <= 500 ? Optional.of(n) : Optional.empty();
    }

    /** True the first time for a report: only then is a message sent. Atomic across threads and processes. */
    boolean markRequested(String id) {
        try {
            Files.createFile(file(id, "requested"));
            return true;
        } catch (FileAlreadyExistsException already) {
            return false;
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    void unmarkRequested(String id) throws IOException {
        Files.deleteIfExists(file(id, "requested"));
    }

    Optional<Status> status(String id) {
        if (Files.exists(pdf(id))) {
            return Optional.of(Status.READY);
        }
        if (Files.exists(file(id, "failed"))) {
            return Optional.of(Status.FAILED);
        }
        return Files.exists(file(id, "requested")) ? Optional.of(Status.QUEUED) : Optional.empty();
    }

    Optional<String> failure(String id) throws IOException {
        Path failed = file(id, "failed");
        return Files.exists(failed) ? Optional.of(Files.readString(failed)) : Optional.empty();
    }

    /** Written next to its final name, then moved: a reader never sees half a PDF. */
    void savePdf(String id, byte[] pdf) throws IOException {
        Path tmp = Files.write(file(id, "pdf.tmp"), pdf);
        Files.move(tmp, pdf(id), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
    }

    void saveFailure(String id, String reason) throws IOException {
        Files.writeString(file(id, "failed"), reason, StandardCharsets.UTF_8);
    }

    Path pdf(String id) {
        return file(id, "pdf");
    }

    private Path file(String id, String kind) {
        return dir.resolve(id + "." + kind);   // id is checked against ID before any file is touched
    }
}
