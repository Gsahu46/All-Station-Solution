package com.kartwala.flashsale;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.Optional;

@Repository
class FlashSaleStore {

    record Purchase(long purchaseId, long saleId, String customerId, long pricePaise) {
    }

    record Sale(long id, int stockLeft, OffsetDateTime startsAt, OffsetDateTime endsAt) {
    }

    private final JdbcClient jdbc;

    FlashSaleStore(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /**
     * The check and the change are one statement: "take one if there is one, while the sale is open". PostgreSQL
     * locks the row for the UPDATE, so 20,000 buyers at once are served one after another on that row, and each
     * sees the stock the previous one left. 0 rows affected means no phone for this buyer. The purchase row is
     * inserted in the same transaction: if it fails (this customer already bought), the phone goes back.
     * Empty when no phone was taken.
     */
    @Transactional
    Optional<Purchase> buy(long saleId, String customerId) {
        int taken = jdbc.sql("""
                        UPDATE flash_sales SET stock_left = stock_left - 1
                         WHERE id = :sale AND stock_left > 0 AND now() >= starts_at AND now() < ends_at""")
                .param("sale", saleId).update();
        if (taken == 0) {
            return Optional.empty();
        }
        return Optional.of(jdbc.sql("""
                        INSERT INTO purchases (sale_id, customer_id, price_paise)
                        SELECT id, :customer, price_paise FROM flash_sales WHERE id = :sale
                        RETURNING id AS purchase_id, sale_id, customer_id, price_paise""")
                .param("sale", saleId).param("customer", customerId).query(Purchase.class).single());
    }

    record Status(long id, String product, int stockLeft, int stockTotal, String status) {
    }

    Optional<Status> status(long saleId) {
        return jdbc.sql("""
                        SELECT id, product, stock_left, stock_total,
                               CASE WHEN now() < starts_at THEN 'UPCOMING'
                                    WHEN now() >= ends_at  THEN 'ENDED'
                                    WHEN stock_left = 0    THEN 'SOLD_OUT'
                                    ELSE 'OPEN' END AS status
                          FROM flash_sales WHERE id = :sale""")
                .param("sale", saleId).query(Status.class).optional();
    }

    /** Deletes the purchase and returns its phone, together. False if there was nothing to cancel. */
    @Transactional
    boolean cancel(long saleId, long purchaseId) {
        int deleted = jdbc.sql("DELETE FROM purchases WHERE id = :id AND sale_id = :sale").param("id", purchaseId).param("sale", saleId).update();
        if (deleted == 0) {
            return false;   // already cancelled, perhaps by a request a moment ago: put nothing back
        }
        jdbc.sql("UPDATE flash_sales SET stock_left = stock_left + 1 WHERE id = :sale").param("sale", saleId).update();
        return true;
    }

    /** Only to explain a refusal: the answer can be a moment old, which is fine for a message. */
    Optional<Sale> sale(long saleId) {
        return jdbc.sql("SELECT id, stock_left, starts_at, ends_at FROM flash_sales WHERE id = :sale")
                .param("sale", saleId).query(Sale.class).optional();
    }
}
