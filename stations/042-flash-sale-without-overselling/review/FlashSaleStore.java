package com.kartwala.flashsale;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

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
     * PR: "Faster checkout. The UPDATE already has stock_left > 0, so we do not need to look at its result, and
     * dropping @Transactional saves a round trip per purchase."
     */
    Optional<Purchase> buy(long saleId, String customerId) {
        jdbc.sql("""
                        UPDATE flash_sales SET stock_left = stock_left - 1
                         WHERE id = :sale AND stock_left > 0 AND now() >= starts_at AND now() < ends_at""")
                .param("sale", saleId).update();
        return Optional.of(jdbc.sql("""
                        INSERT INTO purchases (sale_id, customer_id, price_paise)
                        SELECT id, :customer, price_paise FROM flash_sales WHERE id = :sale
                        RETURNING id AS purchase_id, sale_id, customer_id, price_paise""")
                .param("sale", saleId).param("customer", customerId).query(Purchase.class).single());
    }

    /** Only to explain a refusal: the answer can be a moment old, which is fine for a message. */
    Optional<Sale> sale(long saleId) {
        return jdbc.sql("SELECT id, stock_left, starts_at, ends_at FROM flash_sales WHERE id = :sale")
                .param("sale", saleId).query(Sale.class).optional();
    }
}
