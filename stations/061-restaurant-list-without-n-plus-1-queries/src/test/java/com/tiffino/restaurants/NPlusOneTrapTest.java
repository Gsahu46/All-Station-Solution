package com.tiffino.restaurants;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** Written first: the old home screen counted, then the fix counted, on the same page of 50 Pune restaurants. */
class NPlusOneTrapTest extends ApiTest {

    @Autowired
    OldHomeScreen oldHomeScreen;
    @Autowired
    HomeScreen homeScreen;

    @Test
    void theOldScreenSendsOnePlusFiftyPlusFiftyQueries() {
        Counted<List<HomeScreen.Card>> old = counting(() -> oldHomeScreen.list("pune", 0, 50));
        assertThat(old.result()).hasSize(50);
        assertThat(old.queries()).isEqualTo(1 + 50 + 50);
    }

    @Test
    void theNewScreenSendsThreeQueriesForAnyPageSize() {
        for (int size : new int[]{5, 20, 50}) {
            Counted<HomeScreen.Listing> page = counting(() -> homeScreen.list("pune", 0, size));
            assertThat(page.result().restaurants()).hasSize(size);
            assertThat(page.queries()).as("page size %d", size).isEqualTo(3);
        }
    }

    @Test
    void bothGiveTheSameCards() {
        assertThat(homeScreen.list("pune", 0, 50).restaurants()).isEqualTo(oldHomeScreen.list("pune", 0, 50));
        assertThat(homeScreen.list("mumbai", 0, 20).restaurants()).isEqualTo(oldHomeScreen.list("mumbai", 0, 20));
    }

    @Test
    void aFetchJoinPageLeavesOutRestaurantsWithNoCuisines() {
        jdbc.sql("INSERT INTO cities (code, name) VALUES ('testville', 'Testville')").update();
        try {
            jdbc.sql("INSERT INTO restaurants (city_code, name) VALUES ('testville', 'Aamchi Thali'), ('testville', 'Zunka Bhakar')").update();
            jdbc.sql("INSERT INTO restaurant_cuisines SELECT id, 4 FROM restaurants WHERE name = 'Zunka Bhakar'").update();   // Aamchi Thali has none yet
            Counted<List<String>> fetchJoin = counting(() -> oldHomeScreen.fetchJoinPage("testville", 0, 20));
            assertThat(fetchJoin.queries()).isEqualTo(1);   // Hibernate 7.4 applies the page in SQL, in a subquery
            assertThat(fetchJoin.result()).containsExactly("Zunka Bhakar");
            assertThat(homeScreen.list("testville", 0, 20).restaurants()).extracting(HomeScreen.Card::name).containsExactly("Aamchi Thali", "Zunka Bhakar");
        } finally {
            jdbc.sql("DELETE FROM restaurants WHERE city_code = 'testville'").update();
            jdbc.sql("DELETE FROM cities WHERE code = 'testville'").update();
        }
    }
}
