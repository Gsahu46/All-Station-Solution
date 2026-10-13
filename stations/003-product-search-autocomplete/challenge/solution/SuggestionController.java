package com.kartwala.search;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
class SuggestionController {

    static final int MIN_PREFIX = 2;  // one letter matches too much to be useful
    static final int MAX_PREFIX = 40; // longer than any product name a person types

    private final SuggestionIndex index;

    SuggestionController(SuggestionIndex index) {
        this.index = index;
    }

    @GetMapping("/suggestions")
    Suggestion suggestions(@RequestParam @NotBlank @Size(max = 200) String prefix,
                           @RequestParam(defaultValue = "5") @Min(1) @Max(10) int limit,
                           @RequestParam(defaultValue = "false") boolean includeOutOfStock) {
        // Length is checked after normalising: "  s  " is one letter, not five characters.
        String normalised = SuggestionIndex.normalise(prefix);
        if (normalised.length() < MIN_PREFIX || normalised.length() > MAX_PREFIX) {
            ProblemDetail body = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST,
                    "The prefix must be " + MIN_PREFIX + " to " + MAX_PREFIX + " characters after trimming spaces.");
            body.setTitle("Invalid prefix");
            throw new ErrorResponseException(HttpStatus.BAD_REQUEST, body, null);
        }
        var items = index.suggest(normalised, limit, includeOutOfStock).stream()
                .map(p -> new Suggestion.Item(p.id(), p.name(), p.inStock()))
                .toList();
        return new Suggestion(normalised, items);
    }
}
