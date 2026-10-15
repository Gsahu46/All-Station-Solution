package com.ghoomo.rooms;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The table's rules with Java bypassed, and a rollback. */
class BlockDatabaseTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    void insert(long room, String in, String out) {
        jdbc.sql("INSERT INTO room_blocks (room_id, check_in, check_out, guest_name) VALUES (?, ?::date, ?::date, 'SQL')").params(room, in, out).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        assertThatThrownBy(() -> insert(101, "2026-06-11", "2026-06-13")).hasMessageContaining("room_blocks_no_overlap");
        assertThatThrownBy(() -> insert(101, "2026-07-05", "2026-07-05")).hasMessageContaining("room_blocks_dates_order");
        assertThatThrownBy(() -> insert(999, "2026-07-01", "2026-07-02")).hasMessageContaining("room_blocks_room_fk");
        insert(101, "2026-06-12", "2026-06-15");   // back to back on both sides: allowed by '[)'
        assertThat(blocksOf(101)).isEqualTo(3);
    }

    @Test
    void aGroupBookingIsAllOrNothing() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(status -> {
            insert(102, "2026-07-01", "2026-07-03");
            insert(101, "2026-06-11", "2026-06-12");   // room 101 is held that night: the whole group is refused
        })).hasMessageContaining("room_blocks_no_overlap");
        assertThat(blocksOf(102)).isZero();
    }
}
