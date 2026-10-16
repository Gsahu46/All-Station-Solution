package com.kartwala.catalog;

import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.ErrorResponseException;

import java.time.Instant;
import java.util.List;

@Service
class SellerCatalog {

    record ProductView(long id, String name, long pricePaise, boolean archived, Instant archivedAt, Instant createdAt, Instant updatedAt) {
        static ProductView of(Product p) {
            return new ProductView(p.getId(), p.getName(), p.getPricePaise(), p.getArchivedAt() != null, p.getArchivedAt(), p.getCreatedAt(), p.getUpdatedAt());
        }
    }

    private final ProductRepository products;

    SellerCatalog(ProductRepository products) {
        this.products = products;
    }

    /** "Delete" for a seller means archive: the product leaves the shop, and stays for every order that has it. */
    @Transactional
    void archive(long sellerId, long productId) {
        products.findByIdAndSellerId(productId, sellerId)
                .orElseThrow(() -> notFound(productId))
                .archive();   // managed entity: @PreUpdate stamps updatedAt, and the UPDATE goes out at commit
    }

    @Transactional
    ProductView restore(long sellerId, long productId) {
        Product product = products.findByIdAndSellerId(productId, sellerId).orElseThrow(() -> notFound(productId));
        product.restore();
        try {
            products.flush();   // send the UPDATE now, so the partial unique index answers here, not at commit
        } catch (DataIntegrityViolationException e) {
            throw conflict("Another product of yours on sale already has the name \"" + product.getName() + "\".");
        }
        return ProductView.of(product);
    }

    /** A real DELETE, for archived products only. RESTRICT decides whether any order still points at it. */
    @Transactional
    void purge(long sellerId, long productId) {
        Product product = products.findByIdAndSellerId(productId, sellerId).orElseThrow(() -> notFound(productId));
        if (product.getArchivedAt() == null) {
            throw conflict("Archive product " + productId + " before purging it.");
        }
        try {
            products.delete(product);
            products.flush();
        } catch (DataIntegrityViolationException e) {
            throw conflict("Product " + productId + " is in past orders; it stays archived.");
        }
    }

    static ErrorResponseException conflict(String detail) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, detail);
        p.setTitle("Cannot do that to this product");
        return new ErrorResponseException(HttpStatus.CONFLICT, p, null);
    }

    @Transactional(readOnly = true)
    List<ProductView> list(long sellerId, boolean includeArchived) {
        List<Product> found = includeArchived ? products.findBySellerIdOrderById(sellerId) : products.findBySellerIdAndArchivedAtIsNullOrderById(sellerId);
        return found.stream().map(ProductView::of).toList();
    }

    /** Another seller's product is "not found", not "forbidden": its id says nothing to this seller. */
    static ErrorResponseException notFound(long productId) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, "No product " + productId + " in your catalogue.");
        p.setTitle("Product not found");
        return new ErrorResponseException(HttpStatus.NOT_FOUND, p, null);
    }
}
