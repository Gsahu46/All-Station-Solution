package com.ghoomo.hotels;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowable;

/** Written first. The old string-built search against the same data, then the Specification search given the same input. */
class ConcatenatedSqlTrapTest extends ApiTest {

    @Autowired
    OldHotelSearch old;
    @Autowired
    HotelSearch search;
    @Autowired
    TransactionTemplate transaction;

    private HotelSearch.Filters city(String city) {
        return new HotelSearch.Filters(city, null, null, List.of(), Set.of());
    }

    @Test
    void aQuoteInTheCityTurnsTheFilterOff() {
        assertThat(old.search("goa", null, List.of(), "h.name")).hasSize(6);
        assertThat(old.search("goa' OR '1'='1", null, List.of(), "h.name")).hasSize(9);   // Jaipur too: the filter became always true
        assertThat(search.search(city("goa' OR '1'='1"), "price", 0, 20).total()).isZero();   // bound as a value: no city has that name
    }

    @Test
    void theSortParameterCanRunAnotherStatement() {
        transaction.executeWithoutResult(tx -> {
            Throwable thrown = catchThrowable(() -> old.search("goa", null, List.of(), "h.name; UPDATE hotels SET price_per_night_paise = 50000 --"));
            assertThat(jdbc.sql("SELECT count(*) FROM hotels WHERE price_per_night_paise = 50000").query(Long.class).single())
                    .as("the UPDATE ran (%s)", thrown).isEqualTo(9);
            tx.setRollbackOnly();   // undo it: this test must not leave every hotel at Rs 500
        });
        assertThat(jdbc.sql("SELECT count(*) FROM hotels WHERE price_per_night_paise = 50000").query(Long.class).single()).isZero();
    }

    @Test
    void joiningAmenitiesGaveDuplicatesAndAnyInsteadOfAll() {
        List<String> oldResult = old.search(null, null, List.of("wifi", "breakfast"), "h.name");
        assertThat(oldResult).containsSubsequence("Calangute Sands", "Calangute Sands");   // once per matching amenity
        assertThat(oldResult).contains("Baga Beach Inn");                                  // wifi only: "any of", not "all of"
        assertThat(search.search(new HotelSearch.Filters(null, null, null, List.of(), Set.of("wifi", "breakfast")), "name", 0, 20).hotels())
                .extracting(HotelSearch.Card::name).containsExactly("Calangute Sands", "Fort Aguada Resort", "Panjim Heritage", "Pink City Haveli");
    }
}
