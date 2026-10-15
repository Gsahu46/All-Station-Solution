package com.kartwala.reviews;

import org.junit.jupiter.api.Test;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Challenge 2: GET /admin/rating-drift lists every product whose stored totals differ from a recount of its reviews:
 * productId, storedCount, storedTotal, actualCount, actualTotal, by product id. An empty list means all is well. It
 * reads every review, once, on purpose: a nightly check, not a page view.
 */
class RatingDriftChallengeTest extends ApiTest {

    @Test
    void storedTotalsThatDisagreeWithTheRowsAreListed() throws Exception {
        review(1, 1, 5);
        review(1, 2, 3);
        mvc.perform(get("/admin/rating-drift")).andExpect(status().isOk()).andExpect(content().json("[]", true));
        jdbc.sql("UPDATE product_ratings SET review_count = 3, star_total = 12 WHERE product_id = 1").update();   // a bad manual fix
        jdbc.sql("DELETE FROM reviews WHERE customer_id = 2").update();                                           // and a deleted row
        mvc.perform(get("/admin/rating-drift")).andExpect(content().json("""
                [{"productId":1,"storedCount":3,"storedTotal":12,"actualCount":1,"actualTotal":5}]""", true));
    }
}
