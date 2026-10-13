package com.seatsure.registrations;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * What the form sends. Only these four fields are read: an "id" or "registeredAt" in the JSON is ignored,
 * so a client cannot choose them. Each rule here is checked by Spring before the controller method runs (@Valid).
 */
public record RegistrationRequest(
        @NotBlank @Size(max = 100) String name,
        @NotBlank @Size(max = 254) @Email(message = "must be an email address like name@example.com") String email,
        // Optional. An Indian mobile number: 10 digits starting with 6, 7, 8 or 9 (a demo rule for this station).
        @Pattern(regexp = "[6-9]\\d{9}", message = "must be a 10-digit mobile number") String phone,
        @NotNull @Min(1) @Max(value = 10, message = "at most 10 tickets per registration") Integer tickets) {

    /** Runs before validation: "  Asha  " is stored as "Asha", and "   " becomes "" so @NotBlank rejects it. */
    public RegistrationRequest {
        name = name == null ? null : name.strip();
        email = email == null ? null : email.strip();
        phone = phone == null || phone.isBlank() ? null : phone.strip();
    }
}
