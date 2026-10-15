package com.kartwala.reviews;

import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Slice;
import org.springframework.data.jpa.repository.EntityGraph;
import jakarta.persistence.LockModeType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;

import java.util.Optional;

interface ProductRepository extends JpaRepository<Product, Long> {
}

interface CustomerRepository extends JpaRepository<Customer, Long> {
}

interface PurchaseRepository extends JpaRepository<Purchase, Long> {

    Optional<Purchase> findFirstByCustomerIdAndProductIdAndDeliveredOnIsNotNullOrderById(long customerId, long productId);
}

interface ReviewRepository extends JpaRepository<Review, Long> {

    boolean existsByProductIdAndCustomerId(long productId, long customerId);

    /** SELECT ... FOR UPDATE: a second edit of the same review waits, then reads the stars the first one wrote. */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @EntityGraph(attributePaths = {"product", "customer"})
    Optional<Review> findLockedById(long id);

    /** A Slice, not a Page: a Page would also run count(*) over every review of the product. */
    @EntityGraph(attributePaths = "customer")
    Slice<Review> findByProductIdOrderByIdDesc(long productId, Pageable page);
}

interface ProductRatingRepository extends JpaRepository<ProductRating, Long> {

    /** One atomic UPDATE: PostgreSQL locks the row, so reviews posted at the same moment never overwrite each other. */
    @Modifying
    @Query("UPDATE ProductRating r SET r.reviewCount = r.reviewCount + 1, r.starTotal = r.starTotal + :stars WHERE r.productId = :productId")
    int addReview(long productId, int stars);

    @Modifying
    @Query("UPDATE ProductRating r SET r.starTotal = r.starTotal + :delta WHERE r.productId = :productId")
    int adjustStars(long productId, int delta);
}
