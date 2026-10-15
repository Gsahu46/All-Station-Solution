package com.kartwala.reviews;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 1: PUT /products/{id}/reviews/{reviewId} with {"customerId", "stars", "text"} lets the author change their
 * review. The stored totals move by the difference in stars, in the same transaction. Someone else's review is 403;
 * a review that does not exist, or belongs to another product, is 404. Edits at the same moment must not drift.
 */
class EditReviewChallengeTest extends ApiTest {

    ResultActions edit(long product, long review, long customer, int stars) throws Exception {
        return mvc.perform(put("/products/{id}/reviews/{reviewId}", product, review).contentType(MediaType.APPLICATION_JSON)
                .content("{\"customerId\":%d,\"stars\":%d,\"text\":\"Changed my mind after a month.\"}".formatted(customer, stars)));
    }

    @Test
    void theAuthorChangesStarsAndTheAverageFollows() throws Exception {
        review(1, 1, 5);
        review(1, 2, 4);
        edit(1, 1, 1, 2).andExpect(status().isOk()).andExpect(jsonPath("$.stars").value(2));
        mvc.perform(get("/products/1/rating")).andExpect(content().json("{\"reviewCount\":2,\"averageStars\":3.0}"));
    }

    @Test
    void onlyTheAuthorAndOnlyThatProduct() throws Exception {
        review(1, 1, 5);
        edit(1, 1, 2, 1).andExpect(status().isForbidden());
        edit(2, 1, 1, 1).andExpect(status().isNotFound());
        edit(1, 99, 1, 1).andExpect(status().isNotFound());
        mvc.perform(get("/products/1/rating")).andExpect(jsonPath("$.averageStars").value(5.0));
    }

    @Test
    void editsAtTheSameMomentLeaveTotalsMatchingTheReview() throws Exception {
        review(1, 1, 5);
        List<Integer> statuses = together(10, () -> edit(1, 1, 1, 1 + (int) (Math.random() * 5)).andReturn().getResponse().getStatus());
        assertThat(statuses).containsOnly(200);
        assertThat(jdbc.sql("SELECT star_total FROM product_ratings WHERE product_id = 1").query(Long.class).single())
                .isEqualTo(jdbc.sql("SELECT stars FROM reviews WHERE id = 1").query(Long.class).single());
    }
}
