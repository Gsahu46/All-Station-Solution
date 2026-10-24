package com.bimaly.integration;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Stream;

/**
 * One run per file picked up: what happened to it. Kept as JSON files in data/runs, numbered 1, 2, 3.
 * shortcut: files on one server's disk; with a database in the project, runs belong in a table.
 */
@Component
class Runs {

    enum Status { RUNNING, DONE, DUPLICATE, FAILED, DEAD_LETTERED }

    static final class Run {
        public long id;
        public String file;
        public String checksum;
        public Status status;
        public Instant startedAt;
        public Instant finishedAt;
        public int lines;
        public int accepted;
        public List<PolicyFile.Rejected> rejected = List.of();
        public String error;
    }

    private final Path dir;
    private final JsonMapper json;
    private final AtomicLong last;

    Runs(@Value("${bimaly.files.data}") String data, JsonMapper json) throws IOException {
        this.dir = Files.createDirectories(Path.of(data, "runs"));
        this.json = json;
        try (Stream<Path> files = Files.list(dir)) {
            last = new AtomicLong(files.map(f -> f.getFileName().toString().replace(".json", ""))
                    .filter(n -> n.matches("\\d+")).mapToLong(Long::parseLong).max().orElse(0));
        }
    }

    Run start(String file, String checksum) {
        Run run = new Run();
        run.id = last.incrementAndGet();
        run.file = file;
        run.checksum = checksum;
        run.status = Status.RUNNING;
        run.startedAt = Instant.now();
        return save(run);
    }

    Run finish(Run run, Status status, String error) {
        run.status = status;
        run.error = error;
        run.finishedAt = Instant.now();
        return save(run);
    }

    Optional<Run> find(long id) {
        Path f = dir.resolve(id + ".json");
        return Files.exists(f) ? Optional.of(json.readValue(f.toFile(), Run.class)) : Optional.empty();
    }

    /** Every run of one file name, oldest first (for tests and support). */
    List<Run> forFile(String file) {
        return Stream.iterate(1L, id -> id <= last.get(), id -> id + 1).map(this::find).flatMap(Optional::stream)
                .filter(r -> r.file.equals(file)).toList();
    }

    private Run save(Run run) {
        try {
            Path tmp = Files.createTempFile(dir, "run", ".tmp");
            json.writeValue(tmp.toFile(), run);
            Files.move(tmp, dir.resolve(run.id + ".json"), java.nio.file.StandardCopyOption.REPLACE_EXISTING,
                    java.nio.file.StandardCopyOption.ATOMIC_MOVE);   // a reader never sees half a file
            return run;
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
