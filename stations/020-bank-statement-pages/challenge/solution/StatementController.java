package com.tijori.statements;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;

@RestController
class StatementController {

    /** Deepest offset served (a demo rule). In a database, OFFSET n still reads and skips n rows. */
    static final long MAX_OFFSET = 10_000;

    /** Challenge 2: the size of the amount, debit or credit, then the statement order to break ties. */
    static final Comparator<Transaction> LARGEST_FIRST =
            Comparator.comparingLong((Transaction t) -> Math.abs(t.amountPaise())).reversed().thenComparing(Accounts.STATEMENT_ORDER);

    enum Sort { NEWEST, LARGEST }

    private final Accounts accounts;

    StatementController(Accounts accounts) {
        this.accounts = accounts;
    }

    /** Pages start at 0. Size is bounded, so one request can never ask for the whole history. */
    @GetMapping("/accounts/{id}/transactions")
    Page<Transaction> transactions(@PathVariable String id,
                                   @RequestParam(defaultValue = "0") @Min(0) int page,
                                   @RequestParam(defaultValue = "20") @Min(1) @Max(100) int size,
                                   @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
                                   @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
                                   @RequestParam(defaultValue = "newest") String sort) {
        List<Transaction> statement = accounts.statement(id.toLowerCase(Locale.ROOT)).orElseThrow(() ->
                problem(HttpStatus.NOT_FOUND, "Account not found", "No account has the id " + id + "."));
        if ((long) page * size >= MAX_OFFSET) {
            throw problem(HttpStatus.BAD_REQUEST, "Page too deep",
                    "page x size must be under " + MAX_OFFSET + ". Narrow the request by date instead.");
        }
        if (from != null && to != null && from.isAfter(to)) {
            throw problem(HttpStatus.BAD_REQUEST, "Backwards date range", "from (" + from + ") is after to (" + to + ").");
        }
        Sort order;
        try {
            order = Sort.valueOf(sort.toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException unknown) {
            throw problem(HttpStatus.BAD_REQUEST, "Unknown sort", "sort must be newest or largest.");
        }
        // Challenge 1: filter by posting date, inclusive at both ends.
        List<Transaction> selected = statement.stream()
                .filter(t -> from == null || !t.postedAt().toLocalDate().isBefore(from))
                .filter(t -> to == null || !t.postedAt().toLocalDate().isAfter(to))
                .toList();
        if (order == Sort.LARGEST) {
            selected = selected.stream().sorted(LARGEST_FIRST).toList();
        }
        return Page.of(selected, page, size);
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
