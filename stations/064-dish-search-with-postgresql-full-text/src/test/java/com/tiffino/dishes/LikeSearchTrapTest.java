package com.tiffino.dishes;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** Written first. The old LIKE search on the same 200,008 dishes: what it misses, and what it reads. */
class LikeSearchTrapTest extends ApiTest {

    static final String OLD = "SELECT name FROM dishes WHERE city = :city AND name LIKE '%' || :q || '%' ORDER BY id LIMIT 20";

    private List<String> old(String q) {
        return jdbc.sql(OLD).param("q", q).param("city", "pune").query(String.class).list();
    }

    @Test
    void likeMissesCaseWordOrderPluralsAndDescriptions() {
        assertThat(old("paneer tikka")).isEmpty();                                    // the menu says "Paneer"
        assertThat(old("Paneer Tikka")).containsExactly("Paneer Tikka Masala", "Paneer Tikka", "Tandoori Paneer Tikka Roll");   // not Butter Chicken
        assertThat(old("Tikka Paneer")).isEmpty();
        assertThat(old("Masala Dosas")).isEmpty();
        assertThat(new DishSearchProbe(jdbc).names("paneer tikka")).hasSize(4);
        assertThat(new DishSearchProbe(jdbc).names("Masala Dosas")).hasSize(2);
    }

    @Test
    void likeWithALeadingWildcardReadsEveryDishInTheCityTheGinIndexReadsAFew() {
        Plan like = explain(OLD, Map.of("q", "Paneer", "city", "pune"));   // the old query exactly, spelled as the menu does
        Plan fullText = explain(DishSearch.SQL, Map.of("q", "paneer", "city", "pune"));
        assertThat(like.indexes()).doesNotContain("dishes_search");   // at best it narrows by city, then reads the name of every Pune dish
        assertThat(fullText.indexes()).contains("dishes_search");
        assertThat(like.pages()).isGreaterThan(20 * fullText.pages());
    }

    @Test
    void toTsqueryOnWhatPeopleTypeIsASyntaxError() {
        assertThatThrownBy(() -> jdbc.sql("SELECT to_tsquery('english', :q)").param("q", "paneer tikka").query(String.class).single())
                .rootCause().hasMessageContaining("syntax error in tsquery");
        assertThat(jdbc.sql("SELECT websearch_to_tsquery('english', :q)::text").param("q", "paneer tikka").query(String.class).single())
                .isEqualTo("'paneer' & 'tikka'");
    }

    /** The new search's SQL, read back as names, so the old and new can sit side by side. */
    record DishSearchProbe(org.springframework.jdbc.core.simple.JdbcClient jdbc) {
        List<String> names(String q) {
            return jdbc.sql(DishSearch.SQL).param("q", q).param("city", "pune").query((rs, i) -> rs.getString("name")).list();
        }
    }
}
