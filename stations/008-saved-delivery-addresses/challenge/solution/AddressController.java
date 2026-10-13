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
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import tools.jackson.databind.JsonNode;

import java.net.URI;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
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
    ResponseEntity<Address> get(@PathVariable long customerId, @PathVariable String label) {
        requireCustomer(customerId);
        Address a = book.get(customerId, normalise(label)).orElseThrow(AddressController::notFound);
        return ResponseEntity.ok().eTag(etag(a)).body(a); // challenge 1
    }

    /**
     * Challenge 1: a fingerprint of the address's content. Same content, same ETag, on any server.
     * shortcut: a 32-bit hash can collide; use SHA-256 when a missed conflict would be costly.
     */
    static String etag(Address a) {
        return "\"" + Integer.toHexString(Objects.hash(a.line1(), a.line2(), a.landmark(), a.city(), a.pincode())) + "\"";
    }

    /** Challenge 1: if the client sent If-Match, the address must still be the version it saw. Call inside synchronized (book). */
    private void checkIfMatch(long customerId, String key, String ifMatch) {
        if (ifMatch != null && !book.get(customerId, key).map(AddressController::etag).filter(ifMatch::equals).isPresent()) {
            throw problem(HttpStatus.PRECONDITION_FAILED, "Address changed",
                    "The address changed since you read it. Read it again, then save your change.");
        }
    }

    /** Create or replace the whole address. The same PUT twice leaves the same single address: 201 the first time, then 200. */
    @PutMapping("/{label}")
    ResponseEntity<Address> put(@PathVariable long customerId, @PathVariable String label,
                                @RequestHeader(value = "If-Match", required = false) String ifMatch,
                                @Valid @RequestBody Address address) {
        requireCustomer(customerId);
        String key = normalise(label);
        AddressBook.PutResult result;
        synchronized (book) { // the check and the save are one step: nobody can save in between
            checkIfMatch(customerId, key, ifMatch);
            result = book.put(customerId, key, address);
        }
        return switch (result) {
            case CREATED -> ResponseEntity.created(URI.create("/customers/" + customerId + "/addresses/" + key)).eTag(etag(address)).body(address);
            case REPLACED -> ResponseEntity.ok().eTag(etag(address)).body(address);
            case FULL -> throw problem(HttpStatus.CONFLICT, "Address book full",
                    "A customer can save at most " + AddressBook.MAX_ADDRESSES + " addresses.");
        };
    }

    /** Change only the fields sent (JSON Merge Patch). The address must already exist. */
    @PatchMapping(value = "/{label}", consumes = {"application/merge-patch+json", "application/json"})
    ResponseEntity<Address> patch(@PathVariable long customerId, @PathVariable String label,
                                  @RequestHeader(value = "If-Match", required = false) String ifMatch,
                                  @RequestBody JsonNode patch) {
        requireCustomer(customerId);
        String key = normalise(label);
        synchronized (book) {
            checkIfMatch(customerId, key, ifMatch);
            Address patched = patched(customerId, key, patch);
            book.put(customerId, key, patched);
            return ResponseEntity.ok().eTag(etag(patched)).body(patched);
        }
    }

    private Address patched(long customerId, String key, JsonNode patch) {
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
    static String normalise(String label) {
        String l = label.strip().toLowerCase(Locale.ROOT);
        if (!LABEL.matcher(l).matches()) {
            throw problem(HttpStatus.BAD_REQUEST, "Invalid label", "Labels are 1-20 letters, digits or hyphens, like home or work-2.");
        }
        return l;
    }

    void requireCustomer(long customerId) {
        if (!book.customerExists(customerId)) {
            throw problem(HttpStatus.NOT_FOUND, "Customer not found", "No customer has the id " + customerId + ".");
        }
    }

    private static ErrorResponseException notFound() {
        return problem(HttpStatus.NOT_FOUND, "Address not found", "No saved address has this label.");
    }

    static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail body = ProblemDetail.forStatusAndDetail(status, detail);
        body.setTitle(title);
        return new ErrorResponseException(status, body, null);
    }
}
