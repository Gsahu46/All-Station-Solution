package com.kartwala.reviews;

import jakarta.persistence.EntityManager;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

/**
 * The first test written for this station: the old rating, an average over every review row, recomputed on every
 * product page view. 50,000 reviews of the water bottle (product 2) are written straight to the tables, and
 * PostgreSQL's own EXPLAIN ANALYZE counts the rows each way reads. Row counts, not timings, so the test is stable.
 */
class RecomputedAverageTrapTest extends ApiTest {

    static final int REVIEWS = 50_000;   // enough to see the shape; docs/captures/plans.txt runs 200,000

    @Autowired
    EntityManager entities;
    @Autowired
    TransactionTemplate transaction;
    @Autowired
    JsonMapper json;

    void fiftyThousandReviews() {
        jdbc.sql("INSERT INTO customers (id, name) SELECT 1000 + g, 'Buyer ' || g FROM generate_series(1, ?) g").param(REVIEWS).update();
        jdbc.sql("INSERT INTO purchases (id, customer_id, product_id, delivered_on) SELECT 1000 + g, 1000 + g, 2, DATE '2026-01-01' FROM generate_series(1, ?) g").param(REVIEWS).update();
        // Half five stars, 30% four, 20% two: an average of exactly 4.1.
        jdbc.sql("""
                INSERT INTO reviews (product_id, customer_id, purchase_id, stars, text, created_at)
                SELECT 2, 1000 + g, 1000 + g, CASE WHEN g % 10 < 5 THEN 5 WHEN g % 10 < 8 THEN 4 ELSE 2 END, 'Keeps water cold', now()
                FROM generate_series(1, ?) g""").param(REVIEWS).update();
        // The stored aggregate, backfilled once from the rows, as a migration would when the fix ships.
        jdbc.sql("UPDATE product_ratings SET (review_count, star_total) = (SELECT count(*), sum(stars) FROM reviews WHERE product_id = 2) WHERE product_id = 2").update();
        jdbc.sql("ANALYZE reviews").update();
    }

    /** Rows every scan in the plan really read, one process only (no parallel workers), from EXPLAIN ANALYZE. */
    long rowsRead(String sql) {
        return transaction.execute(status -> {
            jdbc.sql("SET LOCAL max_parallel_workers_per_gather = 0").update();
            String plan = jdbc.sql("EXPLAIN (ANALYZE, FORMAT JSON) " + sql).query(String.class).single();
            return scanned(json.readTree(plan).get(0).get("Plan"));
        });
    }

    static long scanned(JsonNode node) {
        long rows = node.get("Node Type").asString().contains("Scan") ? node.get("Actual Rows").asLong() * node.get("Actual Loops").asLong() : 0;
        if (node.has("Plans")) {
            for (JsonNode child : node.get("Plans")) {
                rows += scanned(child);
            }
        }
        return rows;
    }

    @Test
    void theOldAverageReadsEveryReviewTheStoredOneReadsOneRow() throws Exception {
        fiftyThousandReviews();
        // The old product page: JPQL average and count over the reviews, on every view.
        Object[] old = transaction.execute(status -> (Object[]) entities.createQuery(
                "SELECT avg(r.stars), count(r) FROM Review r WHERE r.product.id = 2").getSingleResult());
        assertThat((Double) old[0]).isEqualTo(4.1, org.assertj.core.data.Offset.offset(1e-9));
        assertThat(rowsRead("SELECT avg(stars), count(*) FROM reviews WHERE product_id = 2")).isEqualTo(REVIEWS);

        // The fix: the same answer, from one row.
        mvc.perform(get("/products/2/rating")).andExpect(jsonPath("$.reviewCount").value(REVIEWS)).andExpect(jsonPath("$.averageStars").value(4.1));
        assertThat(rowsRead("SELECT review_count, star_total FROM product_ratings WHERE product_id = 2")).isEqualTo(1);
    }

    @Test
    void storedAndRecomputedAgreeAfterPostsThroughTheApi() throws Exception {
        review(1, 1, 5);
        review(1, 2, 4);
        Object[] recount = transaction.execute(status -> (Object[]) entities.createQuery(
                "SELECT count(r), sum(r.stars) FROM Review r WHERE r.product.id = 1").getSingleResult());
        assertThat(recount).containsExactly(2L, 9L);
        mvc.perform(get("/products/1/rating")).andExpect(jsonPath("$.reviewCount").value(2)).andExpect(jsonPath("$.averageStars").value(4.5));
    }
}
