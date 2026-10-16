package com.kartwala.prices;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.Clock;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;

@RestController
class PriceController {

    /** Times are the shop's local time, as a seller types them: "2026-11-08T00:00" means midnight in India. */
    record NewPrice(@NotNull @Min(100) @Max(10_000_000) Integer pricePaise, @NotNull LocalDateTime from, LocalDateTime to) {
    }

    private final PriceSchedule schedule;
    private final Clock clock;

    PriceController(PriceSchedule schedule, Clock clock) {
        this.schedule = schedule;
        this.clock = clock;
    }

    @PostMapping("/products/{id}/prices")
    @ResponseStatus(HttpStatus.CREATED)
    PriceSchedule.Schedule set(@PathVariable long id, @Valid @RequestBody NewPrice body) {
        return schedule.set(id, body.pricePaise(), body.from(), body.to());
    }

    @GetMapping("/products/{id}/prices")
    PriceSchedule.Schedule all(@PathVariable long id) {
        return schedule.fullSchedule(id);
    }

    @DeleteMapping("/products/{id}/prices")
    PriceSchedule.Schedule cancel(@PathVariable long id, @RequestParam @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) LocalDateTime from) {
        return schedule.cancel(id, from);
    }

    /** ?at=2026-11-08T00:30+05:30 (an instant, with its offset); now when absent. */
    @GetMapping("/products/{id}/price")
    PriceSchedule.PriceAt price(@PathVariable long id, @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) OffsetDateTime at) {
        return schedule.priceAt(id, at == null ? clock.instant() : at.toInstant());
    }
}
