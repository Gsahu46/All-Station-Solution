package com.taskloom.crm;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.List;
import java.util.Locale;

/** The tenant always comes from the sign-in. A tenant in the body or the query string is not read. */
@RestController
class LeadController {

    static final String STATUSES = "NEW|CONTACTED|QUALIFIED|LOST";

    record NewLead(@NotBlank @Size(max = 100) String name, @NotBlank @Email @Size(max = 254) String email,
                   @Size(max = 100) String company, @Pattern(regexp = STATUSES) String status) {
    }

    private final Leads leads;

    LeadController(Leads leads) {
        this.leads = leads;
    }

    @GetMapping("/leads")
    List<Leads.Lead> search(Authentication user, @RequestParam(required = false) @Pattern(regexp = STATUSES) String status,
                            @RequestParam(required = false) @Size(min = 1, max = 100) String q) {
        return leads.search(SecurityConfig.tenant(user), status, q);
    }

    @GetMapping("/leads/{id}")
    Leads.Lead lead(Authentication user, @PathVariable long id) {
        return leads.find(SecurityConfig.tenant(user), id).orElseThrow(() -> new ErrorResponseException(HttpStatus.NOT_FOUND));
    }

    @PostMapping("/leads")
    ResponseEntity<Leads.Lead> create(Authentication user, @Valid @RequestBody NewLead body) {
        Leads.Lead lead = leads.create(SecurityConfig.tenant(user), body.name().strip(), body.email().strip().toLowerCase(Locale.ROOT),
                body.company() == null || body.company().isBlank() ? null : body.company().strip(),
                body.status() == null ? "NEW" : body.status(), user.getName());
        return ResponseEntity.created(URI.create("/leads/" + lead.id())).body(lead);
    }

    @ExceptionHandler(Leads.EmailTaken.class)
    ProblemDetail emailTaken() {
        return ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, "Your company already has a lead with this email.");
    }
}
