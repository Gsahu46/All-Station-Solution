package com.tiffino.restaurants;

import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;

/** The home screen as it was, kept in the tests only: correct results, one query per restaurant per association. */
@Component
class OldHomeScreen {

    private final OldRestaurants restaurants;
    private final OldReviews reviews;

    OldHomeScreen(OldRestaurants restaurants, OldReviews reviews) {
        this.restaurants = restaurants;
        this.reviews = reviews;
    }

    @Transactional(readOnly = true)
    List<HomeScreen.Card> list(String city, int page, int size) {
        return restaurants.findByCityCodeOrderByNameAscIdAsc(city, PageRequest.of(page, size)).stream().map(r -> {
            List<String> cuisines = r.getCuisines().stream().map(Cuisine::getName).sorted().toList();   // +1 query: the lazy set loads
            List<Review> all = reviews.findByRestaurantId(r.getId());                                  // +1 query: every review row
            HomeScreen.Rating rating = all.isEmpty() ? new HomeScreen.Rating(null, 0)
                    : new HomeScreen.Rating(BigDecimal.valueOf(all.stream().mapToInt(Review::getRating).average().orElseThrow()).setScale(1, RoundingMode.HALF_UP), all.size());
            return new HomeScreen.Card(r.getId(), r.getName(), cuisines, rating);
        }).toList();
    }

    @Transactional(readOnly = true)
    List<String> fetchJoinPage(String city, int page, int size) {
        return restaurants.findWithCuisines(city, PageRequest.of(page, size)).stream().map(Restaurant::getName).toList();
    }
}
