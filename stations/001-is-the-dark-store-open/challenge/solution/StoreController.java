package com.basketo.stores;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

@RestController
class StoreController {

    private static final Pattern STORE_ID = Pattern.compile("[A-Z]{3}-[A-Z]{3}-\\d{2}");

    private final StoreDirectory directory;

    StoreController(StoreDirectory directory) {
        this.directory = directory;
    }

    @GetMapping("/stores/{storeId}/status")
    ResponseEntity<StoreStatus> status(@PathVariable String storeId) {
        // Challenge 1: normalise first. Locale.ROOT, so a Turkish server does not turn "i" into "İ".
        String id = storeId.toUpperCase(Locale.ROOT);
        if (!STORE_ID.matcher(id).matches()) {
            return problem(HttpStatus.BAD_REQUEST, "Invalid store id",
                    "Store ids look like BLR-KOR-01: three capital letters, three capital letters, two digits.");
        }
        return directory.find(id)
                .map(ResponseEntity::ok)
                .orElseGet(() -> problem(HttpStatus.NOT_FOUND, "Store not found", "No dark store has the id " + id + "."));
    }

    /** Challenge 2. A required @RequestParam that is missing is a 400 from Spring itself. */
    @GetMapping("/stores")
    List<StoreStatus> inCity(@RequestParam String city) {
        return directory.inCity(city.toUpperCase(Locale.ROOT));
    }

    private static <T> ResponseEntity<T> problem(HttpStatus status, String title, String detail) {
        ProblemDetail body = ProblemDetail.forStatusAndDetail(status, detail);
        body.setTitle(title);
        return ResponseEntity.of(body).build();
    }
}
