package com.mediqo.reports;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.List;

@RestController
class ReportController {

    /** Demo rule: one report covers at most 92 days (a quarter). */
    static final int MAX_DAYS = 92;

    record DoctorLoad(LocalDate from, LocalDate to, List<DoctorLoadReport.Row> doctors) {
    }

    private final DoctorLoadReport report;

    ReportController(DoctorLoadReport report) {
        this.report = report;
    }

    @GetMapping("/reports/doctor-load")
    DoctorLoad doctorLoad(@RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                          @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
                          @RequestParam(defaultValue = "0") @Min(0) @Max(1000) int minAppointments) {
        if (to.isBefore(from)) {
            throw problem("to is before from.");
        }
        if (ChronoUnit.DAYS.between(from, to) + 1 > MAX_DAYS) {
            throw problem("A report covers at most " + MAX_DAYS + " days.");
        }
        return new DoctorLoad(from, to, report.between(from, to, minAppointments));
    }

    private static ErrorResponseException problem(String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, detail);
        p.setTitle("Invalid date range");
        return new ErrorResponseException(HttpStatus.BAD_REQUEST, p, null);
    }
}
