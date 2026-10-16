package com.taskloom.welcome;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.util.Locale;

@RestController
class SignupController {

    record NewSignup(@NotBlank @Email @Size(max = 254) String email, @NotBlank @Size(max = 80) String name,
                     @Pattern(regexp = "[A-Za-z0-9-]{4,20}") String inviteCode) {
    }

    private final SignupService signups;

    SignupController(SignupService signups) {
        this.signups = signups;
    }

    /** Answers as soon as the sign-up is committed; the welcome email and the CRM follow on their own. */
    @PostMapping("/signups")
    ResponseEntity<SignupService.Signup> signUp(@Valid @RequestBody NewSignup body) {
        SignupService.Signup s = signups.signUp(body.email().strip().toLowerCase(Locale.ROOT), body.name().strip(),
                body.inviteCode() == null ? null : body.inviteCode().toUpperCase(Locale.ROOT));
        return ResponseEntity.created(URI.create("/signups/" + s.id())).body(s);
    }

    /** welcomeEmail: PENDING, SENDING, SENT or DEAD (given up after the last retry). */
    @GetMapping("/signups/{id}")
    SignupService.Signup get(@PathVariable long id) {
        return signups.find(id).orElseThrow(() -> SignupService.problem(HttpStatus.NOT_FOUND, "Sign-up not found", "No sign-up " + id + "."));
    }
}
