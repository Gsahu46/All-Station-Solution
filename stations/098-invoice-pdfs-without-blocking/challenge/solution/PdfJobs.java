package com.billora.invoices;

import com.fasterxml.jackson.annotation.JsonInclude;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.task.TaskRejectedException;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Long-running work as an operation resource, in the shape of Google's AIP-151 (an API design guideline, not a
 * formal standard): a name, done, metadata while it runs, then a response or an error.
 * shortcut: jobs and finished PDFs are kept in this server's memory and never removed; store PDFs in object storage
 * and the jobs in a database, and expire them, before running more than one server.
 */
@Service
class PdfJobs {

    enum State { QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED }

    static final class Job {
        private final UUID id = UUID.randomUUID();
        private final Invoices.Invoice invoice;
        private final Instant createdAt = Instant.now();
        private final AtomicInteger pagesDone = new AtomicInteger();
        private volatile State state = State.QUEUED;
        private volatile byte[] pdf;
        private volatile String error;
        private volatile boolean cancelRequested;

        Job(Invoices.Invoice invoice) {
            this.invoice = invoice;
        }

        Invoices.Invoice invoice() {
            return invoice;
        }

        void started() {
            state = State.RUNNING;
        }

        void pageDone() {
            pagesDone.incrementAndGet();
        }

        /** Challenge 2: checked by the renderer before each page. */
        boolean cancelRequested() {
            return cancelRequested;
        }
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    record Operation(String name, boolean done, Metadata metadata, Result response, Error error) {
    }

    record Metadata(String invoiceId, State state, int pagesDone, int pagesTotal, Instant createdAt) {
    }

    record Result(String pdfUrl, int pages, int bytes) {
    }

    record Error(String code, String message) {
    }

    record Submitted(Operation operation, boolean existing) {
    }

    private static final Logger log = LoggerFactory.getLogger(PdfJobs.class);
    private final Map<UUID, Job> jobs = new ConcurrentHashMap<>();
    private final Map<String, Job> activeByInvoice = new ConcurrentHashMap<>();
    private final Renderer renderer;

    PdfJobs(Renderer renderer) {
        this.renderer = renderer;
    }

    /**
     * Queues a render and returns at once. The same invoice while its job is queued or running gets that job back.
     * Throws TaskRejectedException when the pool and its queue are full.
     */
    Submitted submit(Invoices.Invoice invoice) {
        Job fresh = new Job(invoice);
        Job active = activeByInvoice.putIfAbsent(invoice.id(), fresh);
        if (active != null) {
            return new Submitted(view(active), true);
        }
        try {
            renderer.render(fresh).whenComplete((pdf, failure) -> finish(fresh, pdf, failure));
        } catch (TaskRejectedException full) {
            activeByInvoice.remove(invoice.id(), fresh);
            throw full;
        }
        jobs.put(fresh.id, fresh);
        return new Submitted(view(fresh), false);
    }

    private void finish(Job job, byte[] pdf, Throwable failure) {
        if (job.cancelRequested) {
            job.state = State.CANCELLED;
        } else if (failure != null) {
            // The future's stages wrap what the render threw: report the render's own message.
            Throwable cause = failure instanceof CompletionException && failure.getCause() != null ? failure.getCause() : failure;
            log.warn("PDF job {} for {} failed", job.id, job.invoice.id(), cause);   // logged and kept on the job
            job.error = cause.getMessage();
            job.state = State.FAILED;
        } else {
            job.pdf = pdf;
            job.state = State.SUCCEEDED;
        }
        activeByInvoice.remove(job.invoice.id(), job);
    }

    /** Challenge 2. Empty if there is no such job; throws IllegalStateException if it is already done. */
    Optional<Operation> cancel(UUID id) {
        Job job = jobs.get(id);
        if (job == null) {
            return Optional.empty();
        }
        synchronized (job) {
            if (job.state != State.QUEUED && job.state != State.RUNNING) {
                throw new IllegalStateException("This job is already " + job.state + ".");
            }
            job.cancelRequested = true;
            if (job.state == State.QUEUED) {
                job.state = State.CANCELLED;   // its render will see the flag and stop before the first page
                activeByInvoice.remove(job.invoice.id(), job);
            }
        }
        return Optional.of(view(job));
    }

    Optional<Operation> find(UUID id) {
        return Optional.ofNullable(jobs.get(id)).map(PdfJobs::view);
    }

    /** The PDF of a finished job; empty if there is no such job or it has not succeeded. */
    Optional<byte[]> pdf(UUID id) {
        return Optional.ofNullable(jobs.get(id)).map(j -> j.pdf);
    }

    private static Operation view(Job j) {
        State state = j.state;
        Metadata metadata = new Metadata(j.invoice.id(), state, j.pagesDone.get(), j.invoice.pages(), j.createdAt);
        return switch (state) {
            case SUCCEEDED -> new Operation(name(j), true, metadata, new Result("/pdf-jobs/" + j.id + "/pdf", j.invoice.pages(), j.pdf.length), null);
            case FAILED -> new Operation(name(j), true, metadata, null, new Error("RENDER_FAILED", j.error));
            case CANCELLED -> new Operation(name(j), true, metadata, null, new Error("CANCELLED", "The job was cancelled."));
            default -> new Operation(name(j), false, metadata, null, null);
        };
    }

    private static String name(Job j) {
        return "pdf-jobs/" + j.id;
    }
}
