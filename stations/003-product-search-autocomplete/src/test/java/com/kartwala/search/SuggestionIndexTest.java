package com.kartwala.search;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Locale;

import static org.assertj.core.api.Assertions.assertThat;

/** The index on its own, without Spring. */
class SuggestionIndexTest {

    private final Locale original = Locale.getDefault();

    @AfterEach
    void restoreLocale() {
        Locale.setDefault(original);
    }

    @Test
    void aProductMatchingTwoWordsIsSuggestedOnce() {
        var index = new SuggestionIndex(List.of(new Product(1, "Masala Masala Chai", 10)));
        assertThat(index.suggest("masala", 5)).hasSize(1);
        assertThat(index.candidates("masala")).hasSize(2); // two word starts, one product
    }

    @Test
    void equalPopularityIsOrderedByName() {
        var index = new SuggestionIndex(List.of(new Product(1, "Tea Zesty", 5), new Product(2, "Tea Amber", 5)));
        assertThat(index.suggest("tea", 5)).extracting(Product::name).containsExactly("Tea Amber", "Tea Zesty");
    }

    @Test
    void theRangeEndsWhereThePrefixStopsMatching() {
        var index = new SuggestionIndex(List.of(new Product(1, "Sam", 1), new Product(2, "Samz", 1), new Product(3, "San", 1)));
        assertThat(index.suggest("sam", 5)).extracting(Product::id).containsExactlyInAnyOrder(1L, 2L);
    }

    @Test
    void aTurkishServerLocaleDoesNotChangeMatching() {
        Locale.setDefault(Locale.forLanguageTag("tr-TR")); // "IPHONE".toLowerCase() would be "ıphone"
        var index = new SuggestionIndex(List.of(new Product(1, "Apple iPhone 15", 1)));
        assertThat(index.suggest(SuggestionIndex.normalise("IPHONE"), 5)).hasSize(1);
    }
}
