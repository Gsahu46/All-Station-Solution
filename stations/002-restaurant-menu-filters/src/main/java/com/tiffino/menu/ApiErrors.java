package com.tiffino.menu;

import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.method.annotation.HandlerMethodValidationException;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

import java.util.Map;
import java.util.TreeMap;

/**
 * Spring already turns bad parameters into RFC 9457 problem bodies (the base class). We add an "errors" map,
 * parameter -> message, so the app can say which filter is wrong. Station 006 covers error handling in depth.
 */
@RestControllerAdvice
class ApiErrors extends ResponseEntityExceptionHandler {

    @Override
    protected ResponseEntity<Object> handleHandlerMethodValidationException(
            HandlerMethodValidationException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        Map<String, String> errors = new TreeMap<>();
        ex.getParameterValidationResults().forEach(r -> r.getResolvableErrors()
                .forEach(e -> errors.putIfAbsent(r.getMethodParameter().getParameterName(), e.getDefaultMessage())));
        ex.getBody().setDetail("Some menu filters are invalid.");
        ex.getBody().setProperty("errors", errors);
        return handleExceptionInternal(ex, null, headers, status, request);
    }
}
