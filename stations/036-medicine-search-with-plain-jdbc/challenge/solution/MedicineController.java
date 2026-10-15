package com.mediqo.pharmacy;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.sql.SQLException;
import java.util.List;
import java.util.Locale;

@RestController
class MedicineController {

    record SearchResult(String query, long total, List<Medicine> results) {
    }

    private final MedicineSearch search;

    MedicineController(MedicineSearch search) {
        this.search = search;
    }

    @GetMapping("/medicines")
    SearchResult byName(@RequestParam @NotBlank @Size(min = 2, max = 50) String name,
                        @RequestParam(required = false) @Pattern(regexp = "(?i)TABLET|CAPSULE|SYRUP|CREAM|INJECTION|DROPS") String form,
                        @RequestParam(defaultValue = "20") @Min(1) @Max(20) int size) throws SQLException {
        String text = name.strip();
        MedicineSearch.Page page = search.byName(text, form == null ? null : form.toUpperCase(Locale.ROOT), size);
        return new SearchResult(text, page.total(), page.results());
    }
}
