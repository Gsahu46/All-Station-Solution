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

    PdfJobController(Invoices invoices, PdfJobs jobs) {
        this.invoices = invoices;
        this.jobs = jobs;
    }

    /** 202 and where to look: the request thread is back in the pool in milliseconds, whatever the invoice's size. */
    @PostMapping("/invoices/{id}/pdf-jobs")
    ResponseEntity<PdfJobs.Operation> start(@PathVariable @Pattern(regexp = "INV-\\d{4}-\\d{4}") String id) {
        Invoices.Invoice invoice = invoices.find(id).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No such invoice."));
        PdfJobs.Submitted submitted = jobs.submit(invoice);
        URI location = URI.create("/" + submitted.operation().name());
        return submitted.existing()
                ? ResponseEntity.ok().location(location).body(submitted.operation())   // already queued or running: the same job
                : ResponseEntity.accepted().location(location).body(submitted.operation());
    }

    @GetMapping("/pdf-jobs/{jobId}")
    PdfJobs.Operation job(@PathVariable UUID jobId) {
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
