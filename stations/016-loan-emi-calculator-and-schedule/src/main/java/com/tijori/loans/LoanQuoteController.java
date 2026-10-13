package com.tijori.loans;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.net.URI;
import java.time.Clock;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@RestController
class LoanQuoteController {

    record QuoteRequest(@NotNull Product product,
                        @NotNull @Min(value = 1_000_000, message = "must be at least Rs 10,000")
                        @Max(value = 1_000_000_000, message = "must be at most Rs 1,00,00,000 (a demo rule)") Long principalPaise,
                        @NotNull @Min(6) @Max(360) Integer tenureMonths) {
    }

    record Quote(UUID quoteId, Product product, LocalDate quoteDate, long principalPaise, int tenureMonths,
                 BigDecimal annualRatePercent, LocalDate rateValidFrom, int instalments, long emiPaise, long lastEmiPaise,
                 long totalInterestPaise, long totalPayablePaise) {
    }

    record Schedule(UUID quoteId, List<Emi.Row> rows) {
    }

    private final RateTable rates;
    private final Clock clock;
    private final Map<UUID, Quote> quotes = new ConcurrentHashMap<>();

    LoanQuoteController(RateTable rates, Clock clock) {
        this.rates = rates;
        this.clock = clock;
    }

    @PostMapping("/loan-quotes")
    ResponseEntity<Quote> quote(@Valid @RequestBody QuoteRequest r) {
        LocalDate today = LocalDate.now(clock);
        RateTable.DatedRate rate = rates.rateOn(r.product(), today).orElseThrow(() -> problem(HttpStatus.UNPROCESSABLE_CONTENT,
                "No rate on this date", "There is no " + r.product() + " rate valid on " + today + "."));
        List<Emi.Row> rows = Emi.schedule(r.principalPaise(), rate.annualPercent(), r.tenureMonths());
        long totalInterest = rows.stream().mapToLong(Emi.Row::interestPaise).sum();
        Quote q = new Quote(UUID.randomUUID(), r.product(), today, r.principalPaise(), r.tenureMonths(),
                rate.annualPercent(), rate.from(), rows.size(), rows.getFirst().emiPaise(), rows.getLast().emiPaise(),
                totalInterest, r.principalPaise() + totalInterest);
        quotes.put(q.quoteId(), q);
        return ResponseEntity.created(URI.create("/loan-quotes/" + q.quoteId() + "/schedule")).body(q);
    }

    /** The schedule is recomputed from the stored quote: same inputs, same rate, same rows every time. */
    @GetMapping("/loan-quotes/{id}/schedule")
    Schedule schedule(@PathVariable UUID id) {
        Quote q = quotes.get(id);
        if (q == null) {
            throw problem(HttpStatus.NOT_FOUND, "Quote not found", "No loan quote has this id.");
        }
        return new Schedule(id, Emi.schedule(q.principalPaise(), q.annualRatePercent(), q.tenureMonths()));
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
