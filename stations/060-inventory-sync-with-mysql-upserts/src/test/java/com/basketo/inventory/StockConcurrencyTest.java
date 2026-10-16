package com.basketo.inventory;

import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** Real parallel syncs on virtual threads, released by one latch, against real MySQL locks. */
class StockConcurrencyTest extends ApiTest {

    @Test
    void twoWarehousesSyncingTheSameNewSkusNeverFail() throws Exception {
        for (int round = 1; round <= 5; round++) {
            noStock();
            List<Integer> statuses = together(10, i -> sync(1 + i % 2, items(200, i)).andReturn().getResponse().getStatus());
            assertThat(statuses).as("round %d", round).containsOnly(200);
            assertThat(rows(1)).isEqualTo(200);
            assertThat(rows(2)).isEqualTo(200);
        }
    }

    @Test
    void parallelSnapshotsOfOneWarehouseLeaveOneWholeSnapshot() throws Exception {
        // Odd jobs send their SKUs in reverse order: the sync must not lock in the order it was given.
        List<Integer> statuses = together(10, i -> sync(1, i % 2 == 0 ? items(700, 11 + i) : reversed(items(700, 11 + i))).andReturn().getResponse().getStatus());
        assertThat(statuses).containsOnly(200);
        List<Integer> quantities = jdbc.sql("SELECT DISTINCT quantity FROM stock_levels WHERE warehouse_id = 1").query(Integer.class).list();
        assertThat(rows(1)).isEqualTo(700);
        assertThat(quantities).hasSize(1);   // every row from the same snapshot, never a mix of two counts
        assertThat(quantities.getFirst()).isBetween(11, 20);   // one of the counts sent, not a sum
    }

    private static String reversed(String jsonArray) {
        List<String> objects = Arrays.asList(jsonArray.substring(2, jsonArray.length() - 2).split("\\},\\{"));
        Collections.reverse(objects);
        return "[{" + String.join("},{", objects) + "}]";
    }
}
