package com.tiffino.reports;

import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;

@RestController
class ReportController {

    private final DailySalesReport report;

    ReportController(DailySalesReport report) {
        this.report = report;
    }

    /** ?date=2026-10-14 (ISO). Missing or malformed is a 400 from Spring. */
    @GetMapping("/reports/daily-sales")
    DailySalesReport.Report dailySales(@RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date) {
        return report.forDay(date);
    }
}
