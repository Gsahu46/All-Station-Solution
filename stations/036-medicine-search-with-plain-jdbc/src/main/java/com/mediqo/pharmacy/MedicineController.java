package com.mediqo.pharmacy;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.sql.SQLException;
import java.util.List;

@RestController
class MedicineController {

    record SearchResult(String query, List<Medicine> results) {
    }

    private final MedicineSearch search;

    MedicineController(MedicineSearch search) {
        this.search = search;
    }

    /** Products whose name contains the text, any letter case, at most 20. No match is an empty list, not a 404. */
    @GetMapping("/medicines")
    SearchResult byName(@RequestParam @NotBlank @Size(min = 2, max = 50) String name) throws SQLException {
        String text = name.strip();
        return new SearchResult(text, search.byName(text));
    }
}
