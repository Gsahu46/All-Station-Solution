package com.kartwala.flashsale;

import org.springframework.jdbc.core.simple.JdbcClient;

/**
 * The purchase code before the fix, kept only in tests, on the tables as they were: no constraint on the stock.
 * Read the stock, check it in Java, then update: between the read and the update, other buyers read the same stock.
 */
final class OldFlashSaleStore {

    private OldFlashSaleStore() {
    }

    static void createTables(JdbcClient jdbc, int stock) {
        jdbc.sql("DROP TABLE IF EXISTS old_purchases, old_flash_sales").update();
        jdbc.sql("CREATE TABLE old_flash_sales (id BIGINT PRIMARY KEY, stock_left INT NOT NULL)").update();   // no CHECK
        jdbc.sql("CREATE TABLE old_purchases (sale_id BIGINT NOT NULL, customer_id VARCHAR(10) NOT NULL)").update();
        jdbc.sql("INSERT INTO old_flash_sales VALUES (1, ?)").param(stock).update();
    }

    static boolean buy(JdbcClient jdbc, String customerId) {
        int stock = jdbc.sql("SELECT stock_left FROM old_flash_sales WHERE id = 1").query(Integer.class).single();
        if (stock <= 0) {
            return false;   // "sold out"
        }
        jdbc.sql("UPDATE old_flash_sales SET stock_left = stock_left - 1 WHERE id = 1").update();
        jdbc.sql("INSERT INTO old_purchases (sale_id, customer_id) VALUES (1, ?)").param(customerId).update();
        return true;
    }
}
