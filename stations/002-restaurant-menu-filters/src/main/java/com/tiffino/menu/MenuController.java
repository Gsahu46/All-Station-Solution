package com.tiffino.menu;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import org.springframework.http.HttpStatus;
import org.springframework.web.ErrorResponseException;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
class MenuController {

    private final MenuCatalog catalog;

    MenuController(MenuCatalog catalog) {
        this.catalog = catalog;
    }

    /**
     * Every filter is optional. The constraint annotations are checked by Spring before the method runs;
     * a value outside them is a 400 with one message per parameter (see ApiErrors).
     */
    @GetMapping("/restaurants/{id}/menu")
    Menu menu(@PathVariable long id,
              @RequestParam(required = false) Boolean veg,
              @RequestParam(required = false) @Min(1) @Max(100_000) Integer maxPrice,
              @RequestParam(defaultValue = "recommended")
              @Pattern(regexp = "recommended|price_asc|price_desc", message = "must be recommended, price_asc or price_desc")
              String sort,
              @RequestParam(defaultValue = "20") @Min(1) @Max(50) int limit) {

        Restaurant restaurant = catalog.find(id).orElseThrow(() -> notFound(id));
        var dishes = new MenuQuery(veg, maxPrice, sort, limit).apply(restaurant.dishes());
        return new Menu(restaurant.id(), restaurant.name(), dishes);
    }

    /** An ErrorResponseException becomes a problem+json response without any handler code. */
    private static ErrorResponseException notFound(long id) {
        ProblemDetail body = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No restaurant has the id " + id + ".");
        body.setTitle("Restaurant not found");
        return new ErrorResponseException(HttpStatus.NOT_FOUND, body, null);
    }
}
