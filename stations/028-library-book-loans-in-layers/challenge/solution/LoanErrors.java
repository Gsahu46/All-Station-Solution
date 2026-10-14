package com.citylibrary.loans;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/** One translation of the service's answers into HTTP, shared by both controllers. */
@RestControllerAdvice
class LoanErrors {

    @ExceptionHandler(LoanService.Refused.class)
    ProblemDetail refused(LoanService.Refused e) {
        // Challenge 1: an amount that cannot be right is 422; everything else is a conflict with the record's state.
        HttpStatus status = e.reason == LoanService.Reason.OVERPAYMENT ? HttpStatus.UNPROCESSABLE_CONTENT : HttpStatus.CONFLICT;
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, e.getMessage());
        p.setTitle("Loan refused");
        p.setProperty("reason", e.reason);
        return p;
    }

    @ExceptionHandler(LoanService.NotFound.class)
    ProblemDetail notFound(LoanService.NotFound e) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, e.getMessage());
        p.setTitle("Not found");
        return p;
    }
}
