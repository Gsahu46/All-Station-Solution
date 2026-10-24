package com.mediqo.reports;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.rabbitmq.client.ShutdownSignalException;
import org.springframework.amqp.AmqpException;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.net.URI;

@RestController
class ReportController {

    @JsonInclude(JsonInclude.Include.NON_NULL)
    record ReportState(String reportId, LabReports.Status status, String pdfUrl, String failure) {
    }

    private final LabReports reports;
    private final RabbitTemplate rabbit;

    ReportController(LabReports reports, RabbitTemplate rabbit) {
        this.reports = reports;
        this.rabbit = rabbit;
    }

    /**
     * 202 once the broker has confirmed the message; the render happens on a worker. Asking again for a report that is
     * queued, ready or failed sends nothing new and answers 200 with its state.
     */
    @PostMapping("/lab-reports/{id}/render")
    ResponseEntity<ReportState> render(@PathVariable String id) throws IOException {
        known(id);
        if (!reports.markRequested(id)) {
            return ResponseEntity.ok(state(id));
        }
        try {
            rabbit.invoke(ops -> {
                ops.convertAndSend(ReportsApplication.EXCHANGE, ReportsApplication.ROUTING_KEY, new RenderWorker.RenderRequest(id));
                ops.waitForConfirmsOrDie(5_000);   // throws if the broker does not confirm in 5 s
                return null;
            });
        } catch (AmqpException | ShutdownSignalException brokerDown) {   // a refused confirm arrives as the client's own exception
            reports.unmarkRequested(id);   // nothing was queued: a later request may try again
            throw new ErrorResponseException(HttpStatus.SERVICE_UNAVAILABLE,
                    ProblemDetail.forStatusAndDetail(HttpStatus.SERVICE_UNAVAILABLE, "The render queue is not reachable. Try again shortly."), brokerDown);
        }
        return ResponseEntity.accepted().location(URI.create("/lab-reports/" + id)).body(state(id));
    }

    @GetMapping("/lab-reports/{id}")
    ReportState report(@PathVariable String id) throws IOException {
        known(id);
        if (reports.status(id).isEmpty()) {
            throw problem(HttpStatus.NOT_FOUND, "This report has not been requested.");
        }
        return state(id);
    }

    @GetMapping("/lab-reports/{id}/pdf")
    ResponseEntity<Resource> pdf(@PathVariable String id) {
        known(id);
        if (reports.status(id).orElse(null) != LabReports.Status.READY) {
            throw problem(HttpStatus.NOT_FOUND, "No PDF for this report yet.");
        }
        return ResponseEntity.ok().contentType(MediaType.APPLICATION_PDF).body(new FileSystemResource(reports.pdf(id)));
    }

    private void known(String id) {
        if (!LabReports.ID.matcher(id).matches()) {
            throw problem(HttpStatus.BAD_REQUEST, "A report id looks like LR-0042.");
        }
        reports.pages(id).orElseThrow(() -> problem(HttpStatus.NOT_FOUND, "No such report."));
    }

    private ReportState state(String id) throws IOException {
        LabReports.Status status = reports.status(id).orElseThrow();
        return new ReportState(id, status, status == LabReports.Status.READY ? "/lab-reports/" + id + "/pdf" : null, reports.failure(id).orElse(null));
    }

    private static ErrorResponseException problem(HttpStatus status, String detail) {
        return new ErrorResponseException(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }
}
