package com.tijori.beneficiaries;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

import java.util.Locale;

/**
 * Body of POST /beneficiaries. The messages describe the rule and never repeat what was sent:
 * an error that echoes input can carry an attacker's text into a page or a log.
 */
public record BeneficiaryRequest(
        @NotBlank @Pattern(regexp = "[\\p{L} .'-]{2,100}", message = "must be 2-100 letters, spaces, dots, apostrophes or hyphens")
        String name,
        @NotBlank @Pattern(regexp = "\\d{9,18}", message = "must be 9 to 18 digits") String accountNumber,
        @NotBlank @Pattern(regexp = "[A-Z]{4}0[A-Z0-9]{6}", message = "must be 11 characters like HDFC0001234") String ifsc) {

    /** IFSCs are upper case. Locale.ROOT, so a server set to Turkish does not turn "i" into "İ". */
    public BeneficiaryRequest {
        name = name == null ? null : name.strip();
        accountNumber = accountNumber == null ? null : accountNumber.strip();
        ifsc = ifsc == null ? null : ifsc.strip().toUpperCase(Locale.ROOT);
    }
}
