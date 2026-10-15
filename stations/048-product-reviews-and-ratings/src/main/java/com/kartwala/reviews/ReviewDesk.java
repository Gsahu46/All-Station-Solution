package com.kartwala.reviews;

import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Slice;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

@Service
class ReviewDesk {

    static final int PAGE_SIZE = 10;

    record ReviewView(long id, String customerName, int stars, String text, boolean verifiedPurchase, Instant createdAt) {
        static ReviewView of(Review r) {
            return new ReviewView(r.getId(), r.getCustomer().getName(), r.getStars(), r.getText(), true, r.getCreatedAt());
        }
    }

    record ReviewPage(long productId, int page, int reviewCount, List<ReviewView> reviews, boolean hasNext) {
    }

    record RatingView(long productId, int reviewCount, BigDecimal averageStars) {
    }

    private final ProductRepository products;
    private final CustomerRepository customers;
    private final PurchaseRepository purchases;
    private final ReviewRepository reviews;
    private final ProductRatingRepository ratings;

    ReviewDesk(ProductRepository products, CustomerRepository customers, PurchaseRepository purchases,
               ReviewRepository reviews, ProductRatingRepository ratings) {
        this.products = products;
        this.customers = customers;
        this.purchases = purchases;
        this.reviews = reviews;
        this.ratings = ratings;
    }

    /** The review and the product's totals are written in one transaction: both, or neither. */
    @Transactional
    ReviewView post(long productId, long customerId, int stars, String text) {
        Product product = products.findById(productId).orElseThrow(() -> productNotFound(productId));
        Purchase purchase = purchases.findFirstByCustomerIdAndProductIdAndDeliveredOnIsNotNullOrderById(customerId, productId)
                .orElseThrow(() -> problem(HttpStatus.UNPROCESSABLE_CONTENT, "Not a verified purchase",
                        "Customer " + customerId + " has no delivered order of product " + productId + "."));
        if (reviews.existsByProductIdAndCustomerId(productId, customerId)) {
            throw alreadyReviewed(customerId, productId);
        }
        Review review;
        try {
            review = reviews.save(new Review(product, customers.getReferenceById(customerId), purchase.getId(), stars, text));
        } catch (DataIntegrityViolationException e) {
            // Two posts from the same customer at the same moment both pass the check above; the unique index stops one.
            if (String.valueOf(e.getMessage()).contains("reviews_one_per_customer")) {
                throw alreadyReviewed(customerId, productId);
            }
            throw e;
        }
        if (ratings.addReview(productId, stars) != 1) {
            throw new IllegalStateException("No rating row for product " + productId);   // rolls the review back too
        }
        return ReviewView.of(review);
    }

    @Transactional(readOnly = true)
    ReviewPage page(long productId, int page) {
        ProductRating rating = ratings.findById(productId).orElseThrow(() -> productNotFound(productId));
        Slice<Review> slice = reviews.findByProductIdOrderByIdDesc(productId, PageRequest.of(page, PAGE_SIZE));
        return new ReviewPage(productId, page, rating.getReviewCount(), slice.map(ReviewView::of).getContent(), slice.hasNext());
    }

    /** One primary-key read, however many reviews the product has. */
    @Transactional(readOnly = true)
    RatingView rating(long productId) {
        ProductRating rating = ratings.findById(productId).orElseThrow(() -> productNotFound(productId));
        return new RatingView(productId, rating.getReviewCount(), rating.average());
    }

    private static ErrorResponseException productNotFound(long productId) {
        return problem(HttpStatus.NOT_FOUND, "Product not found", "No product " + productId + ".");
    }

    private static ErrorResponseException alreadyReviewed(long customerId, long productId) {
        return problem(HttpStatus.CONFLICT, "Already reviewed", "Customer " + customerId + " has already reviewed product " + productId + ".");
    }

    static ErrorResponseException problem(HttpStatus status, String title, String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(status, detail);
        p.setTitle(title);
        return new ErrorResponseException(status, p, null);
    }
}
