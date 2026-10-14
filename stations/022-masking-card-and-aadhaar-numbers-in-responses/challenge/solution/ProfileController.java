package com.tijori.profiles;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.security.core.Authentication;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
class ProfileController {

    private final Customers customers;

    ProfileController(Customers customers) {
        this.customers = customers;
    }

    /**
     * A customer sees their own profile; support sees any. Both get the same masked numbers: there is no
     * "show full" switch, because a response is exactly what ends up in logs and screenshots.
     */
    @GetMapping("/customers/{id}/profile")
    Customers.Profile profile(@PathVariable String id, Authentication who) {
        boolean support = who.getAuthorities().stream().anyMatch(a -> a.getAuthority().equals("ROLE_SUPPORT"));
        boolean own = customers.customerOf(who.getName()).map(id::equals).orElse(false);
        if (!support && !own) {
            throw notFound();   // someone else's profile looks exactly like a missing one: no hint that the id exists
        }
        return customers.profile(id).orElseThrow(ProfileController::notFound);
    }

    record AadhaarCheck(@NotNull @Pattern(regexp = "\\d{4}", message = "must be exactly 4 digits") String last4) {
    }

    record CheckResult(boolean match) {
    }

    /** Challenge 2: support checks what a caller reads out. The answer is yes or no; the number never leaves. */
    @PostMapping("/customers/{id}/aadhaar-checks")
    CheckResult checkAadhaar(@PathVariable String id, @Valid @RequestBody AadhaarCheck check) {
        Customers.Profile p = customers.profile(id).orElseThrow(ProfileController::notFound);
        return new CheckResult(p.aadhaar().endsWith(check.last4()));
    }

    /** The id is not echoed: it is whatever the caller typed, scripts included. */
    private static ErrorResponseException notFound() {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No customer profile here for you.");
        p.setTitle("Profile not found");
        return new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
    }
}
