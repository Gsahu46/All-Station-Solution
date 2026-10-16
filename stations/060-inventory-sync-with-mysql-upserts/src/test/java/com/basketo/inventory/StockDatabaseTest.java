package com.basketo.inventory;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DataAccessException;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The rules as MySQL enforces them, written with plain SQL so no Java check runs. */
class StockDatabaseTest extends ApiTest {

    @Autowired
    StockSync stockSync;

    private void insert(long warehouse, String sku, int quantity) {
        jdbc.sql("INSERT INTO stock_levels (warehouse_id, sku, quantity) VALUES (?, ?, ?)").params(warehouse, sku, quantity).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        insert(1, "RICE-5KG", 40);
        assertThatThrownBy(() -> insert(1, "RICE-5KG", 41)).isInstanceOf(DataAccessException.class).hasMessageContaining("stock_levels_warehouse_sku");
        assertThatThrownBy(() -> insert(1, "OIL-1L", -1)).isInstanceOf(DataAccessException.class).hasMessageContaining("stock_levels_quantity_range");
        assertThatThrownBy(() -> insert(1, "oil-1l", 1)).isInstanceOf(DataAccessException.class).hasMessageContaining("stock_levels_sku_shape");
        assertThatThrownBy(() -> insert(99, "OIL-1L", 1)).isInstanceOf(DataAccessException.class).hasMessageContaining("stock_levels_warehouse_fk");
        insert(2, "RICE-5KG", 7);   // the same SKU in another warehouse is another row
        assertThat(rows(1) + rows(2)).isEqualTo(2);
    }

    @Test
    void aBadRowInTheSecondChunkRollsBackTheFirst() {
        List<StockSync.Item> items = new ArrayList<>();
        for (int i = 1; i <= 600; i++) {
            items.add(new StockSync.Item("SKU-%05d".formatted(i), 5));
        }
        items.add(new StockSync.Item("SKU-99999", -3));   // sorted last: row 601, in the second chunk; only the database refuses it
        assertThatThrownBy(() -> stockSync.sync(1, items)).hasMessageContaining("stock_levels_quantity_range");
        assertThat(rows(1)).isZero();   // the 500 rows of the first chunk went back too
    }

    @Test
    void anUpsertUpdatesTheRowInPlace() {
        insert(1, "RICE-5KG", 40);
        long id = jdbc.sql("SELECT id FROM stock_levels WHERE sku = 'RICE-5KG'").query(Long.class).single();
        stockSync.sync(1, List.of(new StockSync.Item("RICE-5KG", 12)));
        assertThat(jdbc.sql("SELECT id FROM stock_levels WHERE sku = 'RICE-5KG'").query(Long.class).single()).isEqualTo(id);
        assertThat(quantity(1, "RICE-5KG")).isEqualTo(12);
    }

    @Test
    void mySqlCountsAnUpsertedRowTwice() {
        String upsert = "INSERT INTO stock_levels (warehouse_id, sku, quantity) VALUES (1, 'RICE-5KG', ?) AS incoming ON DUPLICATE KEY UPDATE quantity = incoming.quantity";
        assertThat(jdbc.sql(upsert).param(40).update()).isEqualTo(1);   // inserted
        assertThat(jdbc.sql(upsert).param(35).update()).isEqualTo(2);   // updated: MySQL reports 2 affected rows
        assertThat(jdbc.sql(upsert).param(35).update()).isEqualTo(1);   // unchanged: Connector/J asks for "found" rows, so 1, not 0
    }
}
