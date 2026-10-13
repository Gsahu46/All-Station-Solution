package com.splitsaathi.groups;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.util.List;
import java.util.Map;

/**
 * Who paid, how much (whole paise), and how to split it:
 * EQUAL among "participants", EXACT with "exactPaise" per person, or SHARES with "shares" per person.
 */
public record ExpenseRequest(
        @NotBlank @Size(max = 80) String description,
        @NotBlank String paidBy,
        @NotNull @Min(1) @Max(value = 10_000_000, message = "must be at most Rs 1,00,000 (a demo rule)") Long amountPaise,
        @NotNull SplitType splitType,
        List<String> participants,
        Map<String, Long> exactPaise,
        Map<String, Integer> shares) {

    public enum SplitType { EQUAL, EXACT, SHARES }
}
