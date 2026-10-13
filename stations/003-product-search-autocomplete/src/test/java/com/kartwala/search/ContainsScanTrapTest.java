package com.kartwala.search;

import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Import;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.IntStream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.contains;
import static org.hamcrest.Matchers.hasItem;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * The first test written for this station: it reproduces the bug before the fix.
 * The customer types "sam" into the search box.
 */
@Import(ContainsScanTrapTest.NaiveSuggestionController.class)
class ContainsScanTrapTest extends ApiTest {

    /** The "before" code: on every keystroke, look at every product name and keep those containing the text. */
    @RestController
    static class NaiveSuggestionController {
        @GetMapping("/naive/suggestions")
        List<String> suggestions(@RequestParam String prefix) {
            return ProductCatalog.PRODUCTS.stream()
                    .map(Product::name)
                    .filter(name -> name.toLowerCase().contains(prefix.toLowerCase()))
                    .toList();
        }
    }

    @Test
    void containsSuggestsBalsamicVinegarForSam() throws Exception {
        mvc.perform(get("/naive/suggestions").param("prefix", "sam"))
                .andExpect(jsonPath("$", hasSize(6)))
                .andExpect(jsonPath("$", hasItem("Balsamic Vinegar 500ml")));  // "sam" in the middle of a word
    }

    @Test
    void theIndexSuggestsOnlyWordStartsMostPopularFirst() throws Exception {
        mvc.perform(get("/suggestions").param("prefix", "sam"))
                .andExpect(jsonPath("$.suggestions[*].name", not(hasItem("Balsamic Vinegar 500ml"))))
                .andExpect(jsonPath("$.suggestions[*].name", contains(
                        "Samsung Galaxy M35 5G", "Samsung Galaxy S24", "Sambar Masala 100g", "Samsung 55-inch Crystal TV", "Samosa Party Pack")));
    }

    @Test
    void withTwoLakhProductsTheScanReadsEveryNameButTheIndexReadsOnlyTheMatches() {
        List<Product> products = new ArrayList<>(ProductCatalog.PRODUCTS);
        IntStream.rangeClosed(1, 200_000).forEach(i -> products.add(new Product(1000 + i, "Item %06d".formatted(i), 1)));

        long namesReadByScan = products.size();                        // contains() has to look at every name
        int entriesReadByIndex = new SuggestionIndex(products).candidates("sam").size();

        assertThat(namesReadByScan).isEqualTo(200_026);
        assertThat(entriesReadByIndex).isEqualTo(5);                   // the five products with a word starting "sam"
    }
}
