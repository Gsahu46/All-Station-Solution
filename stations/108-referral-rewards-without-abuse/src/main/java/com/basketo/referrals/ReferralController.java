package com.basketo.referrals;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;

@RestController
class ReferralController {

    record SignUpRequest(@NotBlank @Size(max = 20) String referralCode, @NotBlank @Size(max = 100) String name,
                         @NotBlank String phone, @NotBlank @Pattern(regexp = "[A-Za-z0-9-]{8,64}") String deviceId) {
    }

    enum OrderStatus { PLACED, DELIVERED, CANCELLED, RETURNED }

    record OrderEvent(@PositiveOrZero long customerId, @PositiveOrZero long totalPaise, @NotNull OrderStatus status) {
    }

    private final Referrals referrals;

    ReferralController(Referrals referrals) {
        this.referrals = referrals;
    }

    @PostMapping("/referrals")
    ResponseEntity<Referrals.SignUp> signUp(@Valid @RequestBody SignUpRequest body) {
        String phone = Phones.normalise(body.phone()).orElseThrow(() -> new ErrorResponseException(HttpStatus.BAD_REQUEST,
                ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "The phone must be an Indian mobile number."), null));
        Referrals.SignUp s = referrals.signUp(body.referralCode(), body.name().strip(), phone, body.deviceId());
        return ResponseEntity.created(URI.create("/customers/" + s.customerId())).body(s);
    }

    /** Only a delivered order qualifies: placing, cancelling or returning one never earns a reward. */
    @PostMapping("/orders/{id}/referral-reward")
    ResponseEntity<Referrals.Result> orderEvent(@PathVariable long id, @Valid @RequestBody OrderEvent body) {
        if (body.status() != OrderStatus.DELIVERED) {
            return ResponseEntity.unprocessableContent().build();
        }
        Referrals.Result r = referrals.orderDelivered(id, body.customerId(), body.totalPaise());
        return ResponseEntity.status(r.outcome() == Referrals.Outcome.REWARDED ? HttpStatus.CREATED : HttpStatus.OK).body(r);
    }

    @GetMapping("/rewards/{id}")
    Referrals.Reward reward(@PathVariable long id) {
        return referrals.reward(id).orElseThrow(() -> new ErrorResponseException(HttpStatus.NOT_FOUND));
    }

    @ExceptionHandler(Referrals.NoSuchCode.class)
    ProblemDetail noSuchCode() {
        return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No customer has this referral code.");
    }

    @ExceptionHandler(Referrals.PhoneTaken.class)
    ProblemDetail phoneTaken() {
        return ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, "This phone number already has a Basketo account.");
    }

    @ExceptionHandler(Referrals.NotANewCustomer.class)
    ProblemDetail notNew(Referrals.NotANewCustomer e) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_CONTENT, e.getMessage());
    }
}
