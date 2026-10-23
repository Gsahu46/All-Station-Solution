package com.billora.invoices;

import jakarta.validation.constraints.Pattern;
import org.springframework.core.task.TaskRejectedException;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.UUID;

@RestController
class PdfJobController {

    private final Invoices invoices;
    private final PdfJobs jobs;
    private final long msPerPage;

    PdfJobController(Invoices invoices, PdfJobs jobs, @org.springframework.beans.factory.annotation.Value("${billora.pdf.ms-per-page}") long msPerPage) {
        this.invoices = invoices;
        this.jobs = jobs;
        this.msPerPage = msPerPage;
    }

    /** Challenge 1: while not done, the seconds the pages left should take, rounded up, at least 1. */
    private <T> ResponseEntity<T> withRetryAfter(ResponseEntity.BodyBuilder response, PdfJobs.Operation job, T body) {
        if (!job.done()) {
            long millis = (long) (job.metadata().pagesTotal() - job.metadata().pagesDone()) * msPerPage;
            response.header("Retry-After", Long.toString(Math.max(1, (millis + 999) / 1000)));
        }
        return response.body(body);
    }

    /** 202 and where to look: the request thread is back in the pool in milliseconds, whatever the invoice's size. */
    @PostMapping("/invoices/{id}/pdf-jobs")
    ResponseEntity<PdfJobs.Operation> start(@PathVariable @Pattern(regexp = "INV-\\d{4}-\\d{4}") String id) {
        Invoices.Invoice invoice = invoices.find(id).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No such invoice."));
        PdfJobs.Submitted submitted = jobs.submit(invoice);
        URI location = URI.create("/" + submitted.operation().name());
        return withRetryAfter(submitted.existing()
                ? ResponseEntity.ok().location(location)   // already queued or running: the same job
                : ResponseEntity.accepted().location(location), submitted.operation(), submitted.operation());
    }

    @GetMapping("/pdf-jobs/{jobId}")
    ResponseEntity<PdfJobs.Operation> get(@PathVariable UUID jobId) {
        PdfJobs.Operation job = job(jobId);
        return withRetryAfter(ResponseEntity.ok(), job, job);
    }

    /** Challenge 2: AIP-151's custom method. 200 with the operation; 409 if it is already done. */
    @org.springframework.web.bind.annotation.PostMapping("/pdf-jobs/{jobId}:cancel")
    PdfJobs.Operation cancel(@PathVariable UUID jobId) {
        try {
            return jobs.cancel(jobId).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No such job."));
        } catch (IllegalStateException done) {
            throw problem(HttpStatus.CONFLICT, done.getMessage());
        }
    }

    private PdfJobs.Operation job(UUID jobId) {
        return jobs.find(jobId).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No such job."));
    }

    @GetMapping("/pdf-jobs/{jobId}/pdf")
    ResponseEntity<byte[]> pdf(@PathVariable UUID jobId) {
        PdfJobs.Operation job = job(jobId);
        byte[] pdf = jobs.pdf(jobId).orElseThrow(() -> problem(HttpStatus.CONFLICT,
                job.done() ? "This job failed: there is no PDF." : "Not ready yet: the job is " + job.metadata().state() + "."));
        return ResponseEntity.ok().contentType(MediaType.APPLICATION_PDF)
                .header("Content-Disposition", ContentDisposition.attachment().filename(job.metadata().invoiceId() + ".pdf").build().toString())
                .body(pdf);
    }

    /** Both workers busy and the queue full: refuse now, with a hint, rather than queue work the user will give up on. */
    @ExceptionHandler(TaskRejectedException.class)
    ResponseEntity<ProblemDetail> busy() {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).header("Retry-After", "30")
                .body(ProblemDetail.forStatusAndDetail(HttpStatus.SERVICE_UNAVAILABLE, "Too many PDFs are being made right now. Try again in a little while."));
    }

    private static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }
}
