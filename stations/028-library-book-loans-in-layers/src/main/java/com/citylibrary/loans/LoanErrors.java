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
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, e.getMessage());
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
