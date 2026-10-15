package com.kartwala.reviews;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

import static org.hamcrest.Matchers.contains;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** The HTTP contract: posting reviews, reading pages and ratings; valid, invalid and not found. */
class ReviewContractTest extends ApiTest {

    @Test
    void aVerifiedBuyerReviewsOnceAndTheRatingMoves() throws Exception {
        review(1, 1, 5).andExpect(status().isCreated()).andExpect(content().json("""
                {"id":1,"customerName":"Asha Verma","stars":5,"text":"Good bass, the battery really lasts.","verifiedPurchase":true}"""));
        review(1, 2, 2).andExpect(status().isCreated());
        mvc.perform(get("/products/1/rating")).andExpect(status().isOk())
                .andExpect(content().json("{\"productId\":1,\"reviewCount\":2,\"averageStars\":3.5}"));
    }

    @Test
    void theSameCustomerCannotReviewTwice() throws Exception {
        review(1, 1, 5).andExpect(status().isCreated());
        review(1, 1, 5).andExpect(status().isConflict()).andExpect(jsonPath("$.title").value("Already reviewed"));
        mvc.perform(get("/products/1/rating")).andExpect(jsonPath("$.reviewCount").value(1));
    }

    @Test
    void onlyDeliveredPurchasesCount() throws Exception {
        review(1, 3, 5).andExpect(status().isUnprocessableContent()).andExpect(jsonPath("$.title").value("Not a verified purchase"));   // on the way
        review(1, 4, 5).andExpect(status().isUnprocessableContent());   // never bought
        review(2, 1, 5).andExpect(status().isUnprocessableContent());   // bought something else
        mvc.perform(get("/products/1/rating")).andExpect(content().json("{\"reviewCount\":0,\"averageStars\":null}"));
    }

    @Test
    void reviewsComeNewestFirstTenAPage() throws Exception {
        deliveredBuyers(11, 1);
        for (long customer = 100; customer <= 110; customer++) {
            review(1, customer, 4).andExpect(status().isCreated());
        }
        mvc.perform(get("/products/1/reviews")).andExpect(status().isOk())
                .andExpect(jsonPath("$.reviews.length()").value(10)).andExpect(jsonPath("$.reviews[0].customerName").value("Buyer 11"))
                .andExpect(jsonPath("$.reviewCount").value(11)).andExpect(jsonPath("$.hasNext").value(true));
        mvc.perform(get("/products/1/reviews").param("page", "1"))
                .andExpect(jsonPath("$.reviews[*].customerName", contains("Buyer 1"))).andExpect(jsonPath("$.hasNext").value(false));
    }

    @Test
    void badReviewsAndPagesAre400() throws Exception {
        for (String body : new String[]{
                "{\"customerId\":1,\"stars\":0,\"text\":\"Bad\"}", "{\"customerId\":1,\"stars\":6,\"text\":\"Great\"}",
                "{\"customerId\":1,\"stars\":5,\"text\":\"  \"}", "{\"customerId\":1,\"text\":\"No stars given\"}",
                "{\"stars\":5,\"text\":\"Who am I\"}", "{\"customerId\":1,\"stars\":4.5,\"text\":\"Half a star\"}"}) {
            mvc.perform(post("/products/1/reviews").contentType(MediaType.APPLICATION_JSON).content(body)).andExpect(status().isBadRequest());
        }
        mvc.perform(get("/products/1/reviews").param("page", "-1")).andExpect(status().isBadRequest());
        mvc.perform(get("/products/1/reviews").param("page", "100")).andExpect(status().isBadRequest());
    }

    @Test
    void unknownProductsAre404() throws Exception {
        review(99, 1, 5).andExpect(status().isNotFound());
        mvc.perform(get("/products/99/rating")).andExpect(status().isNotFound());
        mvc.perform(get("/products/99/reviews")).andExpect(status().isNotFound()).andExpect(jsonPath("$.detail").value("No product 99."));
    }
}
