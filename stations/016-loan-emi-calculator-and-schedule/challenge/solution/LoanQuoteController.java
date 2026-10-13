package com.tijori.loans;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
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
                        @NotNull @Min(6) @Max(360) Integer tenureMonths,
                        LocalDate disbursalDate) {
    }

    record Quote(UUID quoteId, Product product, LocalDate quoteDate, LocalDate disbursalDate, long principalPaise, int tenureMonths,
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
        LocalDate disbursal = r.disbursalDate() == null ? today : r.disbursalDate();
        if (disbursal.isBefore(today) || disbursal.isAfter(today.plusDays(90))) {   // 90 days: a demo rule
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Disbursal date out of range",
                    "The disbursal date must be between " + today + " and " + today.plusDays(90) + ".");
        }
        RateTable.DatedRate rate = rates.rateOn(r.product(), disbursal).orElseThrow(() -> problem(HttpStatus.UNPROCESSABLE_CONTENT,
                "No rate on this date", "There is no " + r.product() + " rate valid on " + disbursal + "."));
        List<Emi.Row> rows = Emi.schedule(r.principalPaise(), rate.annualPercent(), r.tenureMonths());
        long totalInterest = rows.stream().mapToLong(Emi.Row::interestPaise).sum();
        Quote q = new Quote(UUID.randomUUID(), r.product(), today, disbursal, r.principalPaise(), r.tenureMonths(),
                rate.annualPercent(), rate.from(), rows.size(), rows.getFirst().emiPaise(), rows.getLast().emiPaise(),
                totalInterest, r.principalPaise() + totalInterest);
        quotes.put(q.quoteId(), q);
        return ResponseEntity.created(URI.create("/loan-quotes/" + q.quoteId() + "/schedule")).body(q);
    }

    /** The schedule is recomputed from the stored quote: same inputs, same rate, same rows every time. */
    @GetMapping("/loan-quotes/{id}/schedule")
    Schedule schedule(@PathVariable UUID id, @RequestParam(required = false) @Positive Integer prepayMonth,
                      @RequestParam(required = false) @Positive Long prepayPaise) {
        Quote q = quotes.get(id);
        if (q == null) {
            throw problem(HttpStatus.NOT_FOUND, "Quote not found", "No loan quote has this id.");
        }
        List<Emi.Row> plain = Emi.schedule(q.principalPaise(), q.annualRatePercent(), q.tenureMonths());
        if (prepayMonth == null && prepayPaise == null) {
            return new Schedule(id, plain);
        }
        if (prepayMonth == null || prepayPaise == null) {
            throw problem(HttpStatus.BAD_REQUEST, "Incomplete prepayment", "Send both prepayMonth and prepayPaise.");
        }
        if (prepayMonth >= plain.size()) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Prepayment after the last EMI",
                    "The loan has " + plain.size() + " instalments; prepay after month 1 to " + (plain.size() - 1) + ".");
        }
        long left = plain.get(prepayMonth - 1).balancePaise();
        if (prepayPaise >= left) {
            throw problem(HttpStatus.UNPROCESSABLE_CONTENT, "Prepayment is a foreclosure",
                    "After month " + prepayMonth + " the balance is " + left + " paise; a part-prepayment must be less.");
        }
        return new Schedule(id, Emi.schedule(q.principalPaise(), q.annualRatePercent(), q.tenureMonths(), prepayMonth, prepayPaise));
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
