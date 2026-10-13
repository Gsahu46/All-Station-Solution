package com.tiffino.addresses;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Valid;
import jakarta.validation.Validator;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.ErrorResponseException;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.JsonNode;

import java.net.URI;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;
import java.util.regex.Pattern;

/**
 * The URL names the address: /customers/42/addresses/home. So every method is about one known resource:
 * PUT sets it, PATCH changes part of it, DELETE removes it, GET reads it. No POST: POST means "add one more",
 * which is exactly what a retry must not do. Spring answers POST here with 405 and an Allow header.
 */
@RestController
@RequestMapping("/customers/{customerId}/addresses")
class AddressController {

    private static final Pattern LABEL = Pattern.compile("[a-z0-9-]{1,20}");
    private final AddressBook book;
    private final Validator validator;

    AddressController(AddressBook book, Validator validator) {
        this.book = book;
        this.validator = validator;
    }

    @GetMapping
    Map<String, Address> all(@PathVariable long customerId) {
        requireCustomer(customerId);
        return book.all(customerId);
    }

    @GetMapping("/{label}")
    Address get(@PathVariable long customerId, @PathVariable String label) {
        requireCustomer(customerId);
        return book.get(customerId, normalise(label)).orElseThrow(AddressController::notFound);
    }

    /** Create or replace the whole address. The same PUT twice leaves the same single address: 201 the first time, then 200. */
    @PutMapping("/{label}")
    ResponseEntity<Address> put(@PathVariable long customerId, @PathVariable String label, @Valid @RequestBody Address address) {
        requireCustomer(customerId);
        String key = normalise(label);
        return switch (book.put(customerId, key, address)) {
            case CREATED -> ResponseEntity.created(URI.create("/customers/" + customerId + "/addresses/" + key)).body(address);
            case REPLACED -> ResponseEntity.ok(address);
            case FULL -> throw problem(HttpStatus.CONFLICT, "Address book full",
                    "A customer can save at most " + AddressBook.MAX_ADDRESSES + " addresses.");
        };
    }

    /** Change only the fields sent (JSON Merge Patch). The address must already exist. */
    @PatchMapping(value = "/{label}", consumes = {"application/merge-patch+json", "application/json"})
    Address patch(@PathVariable long customerId, @PathVariable String label, @RequestBody JsonNode patch) {
        requireCustomer(customerId);
        String key = normalise(label);
        Address current = book.get(customerId, key).orElseThrow(AddressController::notFound);
        Address patched;
        try {
            patched = MergePatch.apply(current, patch);
        } catch (IllegalArgumentException e) {
            throw problem(HttpStatus.BAD_REQUEST, "Invalid patch", e.getMessage());
        }
        var violations = validator.validate(patched);
        if (!violations.isEmpty()) {
            Map<String, String> errors = new TreeMap<>();
            for (ConstraintViolation<Address> v : violations) {
                errors.putIfAbsent(v.getPropertyPath().toString(), v.getMessage());
            }
            ErrorResponseException ex = problem(HttpStatus.BAD_REQUEST, "Invalid patch", "The patched address would be invalid.");
            ex.getBody().setProperty("errors", errors);
            throw ex;
        }
        book.put(customerId, key, patched);
        return patched;
    }

    /** 204 whether or not it was there: "make sure it is gone" can be retried safely and always gives the same answer. */
    @DeleteMapping("/{label}")
    ResponseEntity<Void> delete(@PathVariable long customerId, @PathVariable String label) {
        requireCustomer(customerId);
        book.delete(customerId, normalise(label));
        return ResponseEntity.noContent().build();
    }

    /** "Home", "HOME" and " home" name the same address. Locale.ROOT so a Turkish server keeps "I" as "i". */
    private static String normalise(String label) {
        String l = label.strip().toLowerCase(Locale.ROOT);
        if (!LABEL.matcher(l).matches()) {
            throw problem(HttpStatus.BAD_REQUEST, "Invalid label", "Labels are 1-20 letters, digits or hyphens, like home or work-2.");
        }
        return l;
    }

    private void requireCustomer(long customerId) {
        if (!book.customerExists(customerId)) {
            throw problem(HttpStatus.NOT_FOUND, "Customer not found", "No customer has the id " + customerId + ".");
        }
    }

    private static ErrorResponseException notFound() {
        return problem(HttpStatus.NOT_FOUND, "Address not found", "No saved address has this label.");
    }

    private static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail body = ProblemDetail.forStatusAndDetail(status, detail);
        body.setTitle(title);
        return new ErrorResponseException(status, body, null);
    }
}
