package com.tiffino.orders;

import org.junit.jupiter.api.Test;

import java.util.HashSet;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The first test written for this station: the in-memory counter repeats, the database sequence does not. */
class InMemoryCounterTrapTest extends ApiTest {

    @Test
    void twoServersWithTheirOwnCountersHandOutTheSameNumbers() {
        OldOrderNumbers serverA = new OldOrderNumbers();
        OldOrderNumbers serverB = new OldOrderNumbers();
        assertThat(serverA.next()).isEqualTo("#1").isEqualTo(serverB.next());
    }

    @Test
    void aRestartStartsTheCounterAgain() {
        OldOrderNumbers beforeRestart = new OldOrderNumbers();
        beforeRestart.next();
        beforeRestart.next();
        OldOrderNumbers afterRestart = new OldOrderNumbers();
        assertThat(afterRestart.next()).isEqualTo("#1");   // the 1st order of the morning, again
    }

    @Test
    void theSequenceIsSharedAndSurvivesARestart() {
        // Two "servers" (two OrderNumbers on the same database), and a third standing in for one restarted.
        OrderNumbers serverA = new OrderNumbers(jdbc);
        OrderNumbers serverB = new OrderNumbers(jdbc);
        Set<String> issued = new HashSet<>();
        for (int i = 0; i < 50; i++) {
            issued.add(serverA.next());
            issued.add(serverB.next());
        }
        issued.add(new OrderNumbers(jdbc).next());
        assertThat(issued).hasSize(101);
    }

    @Test
    void andIfARepeatEverReachedTheTableTheConstraintWouldStopIt() {
        String number = store.place("TF-07", 45_000).orderNumber();
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO orders (order_number, outlet_id, total_paise) VALUES (?, 'TF-02', 100)").param(number).update())
                .hasMessageContaining("orders_number_unique");
    }
}
