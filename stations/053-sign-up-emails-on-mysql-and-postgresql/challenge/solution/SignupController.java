package com.taskloom.signups;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;

@RestController
class SignupController {

    /**
     * Demo rule: ASCII emails only. Lower-casing non-ASCII letters can differ between Java, PostgreSQL and MySQL, and
     * internationalised addresses need their own design. Spaces around the address are trimmed before the check.
     */
    record NewSignup(@NotBlank @Size(max = 254) @Pattern(regexp = "\\s*[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\s*") String email,
                     @NotBlank @Size(max = 80) String name) {
    }

    private final SignupDesk desk;

    SignupController(SignupDesk desk) {
        this.desk = desk;
    }

    @PostMapping("/signups")
    ResponseEntity<SignupDesk.Signup> signUp(@Valid @RequestBody NewSignup body) {
        SignupDesk.Signup signup = desk.signUp(body.email().strip(), body.name().strip());
        return ResponseEntity.created(URI.create("/signups/" + signup.id())).body(signup);
    }

    record NewEmail(@NotBlank @Size(max = 254) @Pattern(regexp = "\\s*[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\s*") String email) {
    }

    @GetMapping("/signups")
    SignupDesk.Signup byEmail(@RequestParam String email) {
        return desk.findByEmail(email.strip()).orElseThrow(() -> notFound("No sign-up with that email."));
    }

    @PatchMapping("/signups/{id}/email")
    SignupDesk.Signup changeEmail(@PathVariable long id, @Valid @RequestBody NewEmail body) {
        return desk.changeEmail(id, body.email().strip()).orElseThrow(() -> notFound("No sign-up " + id + "."));
    }

    static ErrorResponseException notFound(String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, detail);
        p.setTitle("Sign-up not found");
        return new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
    }

    /** Read-back, so a client can confirm what was stored. */
    @GetMapping("/signups/{id}")
    SignupDesk.Signup get(@PathVariable long id) {
        return desk.find(id).orElseThrow(() -> {
            ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No sign-up " + id + ".");
            p.setTitle("Sign-up not found");
            return new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
        });
    }
}
