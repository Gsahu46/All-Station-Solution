package com.basketo.stores;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.regex.Pattern;

@RestController
class StoreController {

    /** Store ids look like BLR-KOR-01: city, area, number. */
    private static final Pattern STORE_ID = Pattern.compile("[A-Z]{3}-[A-Z]{3}-\\d{2}");

    private final StoreDirectory directory;

    StoreController(StoreDirectory directory) {
        this.directory = directory;
    }

    @GetMapping("/stores/{storeId}/status")
    ResponseEntity<StoreStatus> status(@PathVariable String storeId) {
        if (!STORE_ID.matcher(storeId).matches()) {
            return problem(HttpStatus.BAD_REQUEST, "Invalid store id",
                    "Store ids look like BLR-KOR-01: three capital letters, three capital letters, two digits.");
        }
        return directory.find(storeId)
                .map(ResponseEntity::ok)                                   // 200 with the status
                .orElseGet(() -> problem(HttpStatus.NOT_FOUND, "Store not found",
                        "No dark store has the id " + storeId + "."));    // 404, never 200 with an empty body
    }

    /** RFC 9457 problem body: Content-Type application/problem+json with type, title, status, detail, instance. */
    private static <T> ResponseEntity<T> problem(HttpStatus status, String title, String detail) {
        ProblemDetail body = ProblemDetail.forStatusAndDetail(status, detail);
        body.setTitle(title);
        return ResponseEntity.of(body).build();
    }
}
