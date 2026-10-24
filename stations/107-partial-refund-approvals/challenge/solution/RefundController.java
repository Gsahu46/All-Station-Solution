package com.kartwala.refunds;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
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
import org.springframework.web.bind.annotation.RestController;

import java.math.BigDecimal;
import java.net.URI;
import java.text.NumberFormat;
import java.util.Locale;

@RestController
class RefundController {

    record RefundRequest(@Positive @Max(1_000_000_000_000L) long amountPaise, @NotBlank @Size(max = 200) String reason) {
    }

    enum Decision { APPROVE, REJECT }

    record DecisionRequest(@NotNull Decision decision, @Size(max = 200) String note) {
    }

    private final Refunds refunds;

    RefundController(Refunds refunds) {
        this.refunds = refunds;
    }

    @PostMapping("/orders/{id}/refunds")
    ResponseEntity<Refunds.Refund> request(@PathVariable long id, @Valid @RequestBody RefundRequest body, Authentication agent) {
        Refunds.Refund r = refunds.request(id, body.amountPaise(), body.reason().strip(), agent.getName());
        return ResponseEntity.created(URI.create("/refunds/" + r.id())).body(r);
    }

    @PostMapping("/refunds/{id}/approvals")
    Refunds.Refund decide(@PathVariable long id, @Valid @RequestBody DecisionRequest body, Authentication approver) {
        boolean approve = body.decision() == Decision.APPROVE;
        String note = body.note() == null || body.note().isBlank() ? null : body.note().strip();
        if (!approve && note == null) {
            throw new ErrorResponseException(HttpStatus.BAD_REQUEST, ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST,
                    "A rejection needs a note for the customer."), null);
        }
        return refunds.decide(id, approve, note, approver.getName());
    }

    @GetMapping("/orders/{id}")
    Refunds.Order order(@PathVariable long id) {
        return refunds.order(id).orElseThrow(() -> new ErrorResponseException(HttpStatus.NOT_FOUND));
    }

    @ExceptionHandler({Refunds.NoSuchOrder.class, Refunds.NoSuchRefund.class})
    ProblemDetail notFound() {
        return ProblemDetail.forStatus(HttpStatus.NOT_FOUND);
    }

    @ExceptionHandler(Refunds.NotEnoughLeft.class)
    ProblemDetail notEnoughLeft(Refunds.NotEnoughLeft e) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, "Only " + rupees(e.remainingPaise) + " of this order can still be refunded.");
        p.setProperty("remainingPaise", e.remainingPaise);
        return p;
    }

    @ExceptionHandler(Refunds.AlreadyDecided.class)
    ProblemDetail alreadyDecided(Refunds.AlreadyDecided e) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, "This refund is already " + e.status + ".");
    }

    @ExceptionHandler(Refunds.OwnRequest.class)
    ResponseEntity<ProblemDetail> ownRequest() {
        return ResponseEntity.status(HttpStatus.FORBIDDEN).body(ProblemDetail.forStatusAndDetail(HttpStatus.FORBIDDEN,
                "You asked for this refund; another approver must decide it."));
    }

    @ExceptionHandler(Refunds.SameApprover.class)
    ResponseEntity<ProblemDetail> sameApprover() {
        return ResponseEntity.status(HttpStatus.FORBIDDEN).body(ProblemDetail.forStatusAndDetail(HttpStatus.FORBIDDEN,
                "You gave the first approval; a different approver must give the second."));
    }

    /** ₹12,500.00, grouped the Indian way (₹1,25,000.00). */
    static String rupees(long paise) {
        return NumberFormat.getCurrencyInstance(Locale.of("en", "IN")).format(BigDecimal.valueOf(paise, 2));
    }
}
