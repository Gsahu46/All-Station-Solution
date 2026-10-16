package com.tiffino.dishes;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Locale;

@RestController
class DishController {

    private final DishSearch search;

    DishController(DishSearch search) {
        this.search = search;
    }

    @GetMapping("/dishes/search")
    DishSearch.Results search(@RequestParam @Size(min = 2, max = 100) String q,
                              @RequestParam @Pattern(regexp = "[A-Za-z-]{3,30}") String city,
                              @RequestParam(required = false) @Min(0) @Max(5000) Integer maxPrice) {
        return search.search(q.strip(), city.toLowerCase(Locale.ROOT), maxPrice == null ? Integer.MAX_VALUE : maxPrice * 100);
    }
}
