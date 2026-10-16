package com.tiffino.restaurants;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Locale;

@RestController
class RestaurantController {

    private final HomeScreen homeScreen;

    RestaurantController(HomeScreen homeScreen) {
        this.homeScreen = homeScreen;
    }

    /** Demo limits: up to 50 restaurants a page, up to page 1000. */
    @GetMapping("/restaurants")
    HomeScreen.Listing list(@RequestParam @Pattern(regexp = "[A-Za-z-]{3,30}") String city,
                            @RequestParam(defaultValue = "0") @Min(0) @Max(1000) int page,
                            @RequestParam(defaultValue = "20") @Min(1) @Max(50) int size,
                            @RequestParam(required = false) @Size(max = 50) String cuisine,
                            @RequestParam(defaultValue = "name") @Pattern(regexp = "name|rating") String sort) {
        return homeScreen.list(city.toLowerCase(Locale.ROOT), cuisine, sort.equals("rating"), page, size);
    }
}
