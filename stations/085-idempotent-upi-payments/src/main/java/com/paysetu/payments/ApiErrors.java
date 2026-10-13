package com.paysetu.payments;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.method.ParameterErrors;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

import java.util.Map;
import java.util.TreeMap;

/**
 * Every error is an RFC 9457 problem+json body. The base class already does that for
 * missing headers, bad JSON, 404s and our ErrorResponseExceptions; we only add an
 * "errors" map (field -> message) so a client can show each message next to its input.
 * Because the header has a constraint, Spring validates the whole method, so body
 * errors also arrive here (not as MethodArgumentNotValidException).
 */
@RestControllerAdvice
class ApiErrors extends ResponseEntityExceptionHandler {

    @Override
    protected ResponseEntity<Object> handleHandlerMethodValidationException(
            HandlerMethodValidationException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        Map<String, String> errors = new TreeMap<>();
        ex.getParameterValidationResults().forEach(result -> {
            if (result instanceof ParameterErrors body) {
                body.getFieldErrors().forEach(e -> errors.putIfAbsent(e.getField(), e.getDefaultMessage()));
            } else {
                String name = result.getMethodParameter().getParameterName();
                result.getResolvableErrors().forEach(e -> errors.putIfAbsent(name, e.getDefaultMessage()));
            }
        });
        ex.getBody().setDetail("The payment request has invalid fields.");
        ex.getBody().setProperty("errors", errors);
        return handleExceptionInternal(ex, null, headers, status, request);
    }
}
