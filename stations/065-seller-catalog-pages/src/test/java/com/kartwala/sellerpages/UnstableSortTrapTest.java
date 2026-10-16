package com.kartwala.sellerpages;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Slice;
import org.springframework.data.domain.Sort;
import org.springframework.transaction.support.TransactionTemplate;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** Written first. Every page of seller 7's 2,000 products, sorted the old way and the new way. */
class UnstableSortTrapTest extends ApiTest {

    @Autowired
    ProductRepository products;
    @Autowired
    SellerCatalog catalog;
    @Autowired
    OldProducts old;
    @Autowired
    TransactionTemplate transaction;

    /**
     * Every page, as a seller would click through them, inside one transaction where PostgreSQL must sort rather
     * than read an index: the plan it picks whenever the statistics say so. With an index in (price, id) order the
     * ties happen to come out stable; nothing in SQL promises that.
     */
    private List<Long> everyPageSorted(java.util.function.IntFunction<Iterable<ProductCard>> page) {
        return transaction.execute(tx -> {
            jdbc.sql("SET LOCAL enable_indexscan = off").update();
            jdbc.sql("SET LOCAL enable_indexonlyscan = off").update();
            jdbc.sql("SET LOCAL enable_bitmapscan = off").update();
            List<Long> seen = new ArrayList<>();
            for (int p = 0; p < 100; p++) {
                page.apply(p).forEach(card -> seen.add(card.id()));
            }
            return seen;
        });
    }

    @Test
    void sortingByPriceAloneRepeatsSomeProductsAndNeverShowsOthers() {
        List<Long> seen = everyPageSorted(p -> products.findBySellerId(7, PageRequest.of(p, 20, Sort.by("pricePaise"))));   // the old code
        assertThat(seen).hasSize(2000);
        assertThat(new HashSet<>(seen)).hasSizeLessThan(2000);   // 2,000 rows shown, fewer distinct products: repeats, so others vanished
    }

    @Test
    void withIdAsTheTieBreakerEveryProductAppearsExactlyOnce() {
        List<Long> seen = everyPageSorted(p -> catalog.page(7, PageRequest.of(p, 20, Sort.by("pricePaise"))));
        assertThat(seen).hasSize(2000).doesNotHaveDuplicates();
    }

    @Test
    void aPageCountsEveryTimeASliceOnlyLooksOneRowAhead() {
        Counted<Page<ProductCard>> page = counting(() -> catalog.page(7, PageRequest.of(3, 20, Sort.by("name"))));
        Counted<Slice<ProductCard>> slice = counting(() -> old.findSliceBySellerId(7, PageRequest.of(3, 20, Sort.by("name", "id"))));
        assertThat(page.queries()).isEqualTo(3);    // does the seller exist, the rows, and the count
        assertThat(slice.queries()).isEqualTo(1);   // the rows only (21 of them, to know about a next page)
        assertThat(slice.result().getContent()).isEqualTo(page.result().getContent());
        assertThat(slice.result().hasNext()).isTrue();
    }
}
