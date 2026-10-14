package com.bimaly.premiums;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
class PremiumQuoteController {

    /** Oldest age we quote online (a demo rule); older travellers are referred to an agent. */
    static final int MAX_ONLINE_AGE = 80;

    record QuoteRequest(@NotNull @Min(0) @Max(120) Integer age, @NotNull Trip.Destination destination,
                        @NotNull @Min(1) @Max(180) Integer days, Boolean adventureSports) {
        // Boolean, not boolean: the field is optional, and Jackson 3 rejects a missing primitive (FAIL_ON_NULL_FOR_PRIMITIVES)
    }

    private final PremiumCalculator calculator;

    PremiumQuoteController(PremiumCalculator calculator) {
        this.calculator = calculator;
    }

    /** A quote only: no policy is issued and nothing is charged. */
    @PostMapping("/premium-quotes")
    PremiumCalculator.Quote quote(@Valid @RequestBody QuoteRequest r) {
        if (r.age() > MAX_ONLINE_AGE) {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_CONTENT,
                    "Online quotes cover travellers up to " + MAX_ONLINE_AGE + ". An agent can quote for older travellers.");
            p.setTitle("No online cover for this age");
            throw new ErrorResponseException(HttpStatus.UNPROCESSABLE_CONTENT, p, null);
        }
        return calculator.quote(new Trip(r.age(), r.destination(), r.days(), Boolean.TRUE.equals(r.adventureSports())));
    }
}
