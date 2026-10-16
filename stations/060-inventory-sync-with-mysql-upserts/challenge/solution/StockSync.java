package com.basketo.inventory;

import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Optional;

/**
 * Writes a warehouse's stock snapshot with one MySQL upsert per chunk: no SELECT first, so there is no gap between
 * "not there" and "insert" for another sync to fall into.
 */
@Service
class StockSync {

    record Item(String sku, int quantity) {
    }

    record Synced(long warehouseId, int syncedItems, long skusInWarehouse, int zeroedSkus) {
    }

    record Level(long warehouseId, String sku, int quantity) {
    }

    Optional<Level> level(long warehouseId, String sku) {
        return jdbc.sql("SELECT warehouse_id, sku, quantity FROM stock_levels WHERE warehouse_id = ? AND sku = ?")
                .params(warehouseId, sku).query(Level.class).optional();
    }

    /** Rows per statement. Each row is 3 parameters; 500 rows stays far below MySQL's 65,535 placeholders. */
    static final int CHUNK = 500;

    private final JdbcClient jdbc;

    StockSync(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional
    Synced sync(long warehouseId, List<Item> items) {
        // One sync per warehouse at a time: a second one waits here, on one row, until the first commits. Without it,
        // parallel syncs of one warehouse deadlocked often inside InnoDB; the retry in StockController covers the rare rest.
        if (jdbc.sql("SELECT id FROM warehouses WHERE id = ? FOR UPDATE").param(warehouseId).query(Long.class).optional().isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "No warehouse " + warehouseId);
        }
        for (int from = 0; from < items.size(); from += CHUNK) {
            upsert(warehouseId, items.subList(from, Math.min(from + CHUNK, items.size())));
        }
        long skus = jdbc.sql("SELECT count(*) FROM stock_levels WHERE warehouse_id = ?").param(warehouseId).query(Long.class).single();
        return new Synced(warehouseId, items.size(), skus, 0);
    }

    /** Challenge 2: the snapshot is everything on the shelves; SKUs it does not mention go to 0, in the same transaction. */
    @Transactional
    Synced syncFull(long warehouseId, List<Item> items) {
        Synced synced = sync(warehouseId, items);   // joins this transaction; the warehouse row stays locked until commit
        List<Object> params = new ArrayList<>(List.of(warehouseId));
        items.forEach(item -> params.add(item.sku()));
        int zeroed = jdbc.sql("UPDATE stock_levels SET quantity = 0 WHERE warehouse_id = ? AND quantity <> 0 AND sku NOT IN ("
                + String.join(", ", Collections.nCopies(items.size(), "?")) + ")").params(params).update();
        return new Synced(warehouseId, items.size(), synced.skusInWarehouse(), zeroed);
    }

    private void upsert(long warehouseId, List<Item> chunk) {
        // MySQL 8.0.19+ row alias; VALUES(quantity) in the update is deprecated.
        String sql = "INSERT INTO stock_levels (warehouse_id, sku, quantity) VALUES "
                + String.join(", ", Collections.nCopies(chunk.size(), "(?, ?, ?)"))
                + " AS incoming ON DUPLICATE KEY UPDATE quantity = incoming.quantity";
        List<Object> params = new ArrayList<>(chunk.size() * 3);
        for (Item item : chunk) {
            params.add(warehouseId);
            params.add(item.sku());
            params.add(item.quantity());
        }
        jdbc.sql(sql).params(params).update();
    }
}
