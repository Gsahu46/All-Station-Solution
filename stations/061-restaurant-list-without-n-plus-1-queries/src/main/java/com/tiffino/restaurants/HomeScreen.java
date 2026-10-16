package com.tiffino.restaurants;

import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/** The home screen's restaurant list in three queries, however many restaurants a page holds. */
@Service
class HomeScreen {

    record Rating(BigDecimal average, long count) {
    }

    record Card(long id, String name, List<String> cuisines, Rating rating) {
    }

    record Listing(String city, int page, int size, List<Card> restaurants) {
    }

    private final RestaurantRepository restaurants;
    private final ReviewRepository reviews;
    private final CityRepository cities;

    HomeScreen(RestaurantRepository restaurants, ReviewRepository reviews, CityRepository cities) {
        this.restaurants = restaurants;
        this.reviews = reviews;
        this.cities = cities;
    }

    @Transactional(readOnly = true)
    Listing list(String city, int page, int size) {
        List<Long> ids = restaurants.findPageOfIds(city, PageRequest.of(page, size));
        if (ids.isEmpty()) {
            // Only an empty page needs to know whether the city exists: the usual path stays at three queries.
            if (!cities.existsById(city)) {
                throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Tiffino does not deliver in " + city + " yet");
            }
            return new Listing(city, page, size, List.of());
        }
        Map<Long, Restaurant> byId = restaurants.findByIdIn(ids).stream().collect(Collectors.toMap(Restaurant::getId, Function.identity()));
        Map<Long, RatingSummary> ratings = reviews.summariesFor(ids).stream().collect(Collectors.toMap(RatingSummary::restaurantId, Function.identity()));
        List<Card> cards = ids.stream().map(id -> card(byId.get(id), ratings.get(id))).toList();   // back in page order
        return new Listing(city, page, size, cards);
    }

    private static Card card(Restaurant r, RatingSummary rating) {
        List<String> cuisines = r.getCuisines().stream().map(Cuisine::getName).sorted().toList();
        Rating summary = rating == null ? new Rating(null, 0)
                : new Rating(BigDecimal.valueOf(rating.average()).setScale(1, RoundingMode.HALF_UP), rating.count());
        return new Card(r.getId(), r.getName(), cuisines, summary);
    }
}
