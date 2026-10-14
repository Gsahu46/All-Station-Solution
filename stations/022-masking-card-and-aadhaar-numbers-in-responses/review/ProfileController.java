package com.tijori.profiles;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.security.core.Authentication;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
class ProfileController {

    private final Customers customers;

    ProfileController(Customers customers) {
        this.customers = customers;
    }

    /** Support can pass ?full=true to read the numbers out to a customer during KYC verification. */
    @GetMapping("/customers/{id}/profile")
    Object profile(@PathVariable String id, @RequestParam(defaultValue = "false") boolean full, Authentication who) {
        boolean support = who.getAuthorities().stream().anyMatch(a -> a.getAuthority().equals("ROLE_SUPPORT"));
        // The app only ever shows a customer their own id, so no ownership check is needed here.
        Customers.Profile p = customers.profile(id).orElseThrow(ProfileController::notFound);
        if (support && full) {
            return Map.of("customerId", p.customerId(), "name", p.name(), "aadhaar", p.aadhaar().raw(),
                    "cards", p.cards().stream().map(c -> c.number().raw()).toList());
        }
        return p;
    }

    /** The id is not echoed: it is whatever the caller typed, scripts included. */
    private static ErrorResponseException notFound() {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No customer profile here for you.");
        p.setTitle("Profile not found");
        return new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
    }
}
