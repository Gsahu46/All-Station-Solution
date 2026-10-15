package com.kartwala.reviews;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
class ReviewController {

    /** Demo: the customer is named in the body. A real shop takes it from the login, never from the client. */
    record NewReview(@NotNull Long customerId, @Min(1) @Max(5) int stars, @NotBlank @Size(max = 2000) String text) {
    }

    private final ReviewDesk desk;

    ReviewController(ReviewDesk desk) {
        this.desk = desk;
    }

    @PostMapping("/products/{id}/reviews")
    @ResponseStatus(HttpStatus.CREATED)
    ReviewDesk.ReviewView post(@PathVariable long id, @Valid @RequestBody NewReview body) {
        return desk.post(id, body.customerId(), body.stars(), body.text().strip());
    }

    /** Demo limit: 100 pages of 10. Deep OFFSET pages get slower; real shops page by "reviews before id X". */
    @GetMapping("/products/{id}/reviews")
    ReviewDesk.ReviewPage page(@PathVariable long id, @RequestParam(defaultValue = "0") @Min(0) @Max(99) int page) {
        return desk.page(id, page);
    }

    @GetMapping("/products/{id}/rating")
    ReviewDesk.RatingView rating(@PathVariable long id) {
        return desk.rating(id);
    }
}
