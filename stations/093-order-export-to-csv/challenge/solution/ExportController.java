package com.kartwala.export;

import jakarta.validation.constraints.Pattern;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.Map;

@RestController
class ExportController {

    /** Demo rule: at most 366 days, both ends included. */
    static final int MAX_DAYS = 366;

    /** Demo sellers: sign-in name to seller id. The seller always comes from the sign-in, never from the request. */
    static final Map<String, Long> SELLERS = Map.of("neha.store", 1L, "arun.mart", 2L);

    private final OrderExport export;

    ExportController(OrderExport export) {
        this.export = export;
    }

    record ExportEntry(LocalDate from, LocalDate to, java.time.OffsetDateTime exportedAt, Integer rowsSent) {
    }

    /** The seller's own exports, newest first; rowsSent is empty while one runs or if it was cut off. */
    @GetMapping("/seller/exports")
    java.util.List<ExportEntry> exports(Authentication who) {
        return export.history(SELLERS.get(who.getName()));
    }

    /** The CSV is written while it is read from the database, so a year of orders never sits in memory. */
    @GetMapping("/seller/orders/export")
    ResponseEntity<StreamingResponseBody> export(@RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                                 @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
                                                 @RequestParam(required = false) @Pattern(regexp = "PLACED|SHIPPED|DELIVERED|CANCELLED") String status,
                                                 Authentication who) {
        if (to.isBefore(from) || ChronoUnit.DAYS.between(from, to) >= MAX_DAYS) {
            throw new ErrorResponseException(HttpStatus.BAD_REQUEST,
                    ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "from must be on or before to, and at most a year apart"), null);
        }
        long seller = SELLERS.get(who.getName());
        long logId = export.log(seller, from, to);
        StreamingResponseBody body = out -> export.write(logId, seller, from, to, status, out);
        return ResponseEntity.ok()
                .contentType(new MediaType("text", "csv", java.nio.charset.StandardCharsets.UTF_8))
                .header(HttpHeaders.CONTENT_DISPOSITION, ContentDisposition.attachment().filename("orders-" + from + "-to-" + to + ".csv").build().toString())
                .body(body);
    }
}
