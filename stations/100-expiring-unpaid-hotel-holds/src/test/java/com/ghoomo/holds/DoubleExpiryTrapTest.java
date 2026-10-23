package com.ghoomo.holds;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.Duration;
import java.time.LocalDate;
import java.util.List;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.Executors;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Christmas Eve, five deluxe rooms, all held; one hold is unpaid and expires. Two servers run the clean-up at the
 * same moment. Written first.
 */
class DoubleExpiryTrapTest extends ApiTest {

    @Autowired
    PlatformTransactionManager transactions;

    void fiveHoldsOneOfThemDue() throws Exception {
        hold("unpaid-0001", 1, "2026-12-24", "late@example.com").andExpect(status().isCreated());
        CLOCK.advance(Duration.ofMinutes(10));
        for (int i = 2; i <= 5; i++) {
            hold("paying-000" + i, 1, "2026-12-24", "guest" + i + "@example.com").andExpect(status().isCreated());
        }
        CLOCK.advance(Duration.ofMinutes(6));   // the first is 16 minutes old: due; the others 6
        assertThat(held(1, "2026-12-24")).isEqualTo(5);
    }

    /** The old job: read what is due, then give each room back and mark the hold, whatever happened in between. */
    void oldJob(CyclicBarrier bothHaveRead) {
        record Due(long id, long roomTypeId, LocalDate stayDate) {
        }
        new TransactionTemplate(transactions).executeWithoutResult(tx -> {
            List<Due> due = jdbc.sql("SELECT id, room_type_id, stay_date FROM holds WHERE status = 'HELD' AND expires_at <= ?")
                    .param(java.time.OffsetDateTime.ofInstant(CLOCK.instant(), java.time.ZoneOffset.UTC)).query(Due.class).list();
            try {
                bothHaveRead.await();   // two servers, the same schedule: both read before either writes
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
            for (Due d : due) {
                jdbc.sql("UPDATE room_nights SET held = held - 1 WHERE room_type_id = ? AND stay_date = ?").params(d.roomTypeId(), d.stayDate()).update();
                jdbc.sql("UPDATE holds SET status = 'EXPIRED', expired_at = now() WHERE id = ?").param(d.id()).update();
            }
        });
    }

    @Test
    void theOldJobOnTwoServersGivesOneRoomBackTwiceAndTheHotelIsOverbooked() throws Exception {
        fiveHoldsOneOfThemDue();
        CyclicBarrier barrier = new CyclicBarrier(2);
        try (var servers = Executors.newVirtualThreadPerTaskExecutor()) {
            servers.submit(() -> oldJob(barrier));
            servers.submit(() -> oldJob(barrier));
        }
        assertThat(held(1, "2026-12-24")).isEqualTo(3);   // one hold expired, two rooms given back
        hold("walk-in-0001", 1, "2026-12-24", "a@example.com").andExpect(status().isCreated());
        hold("walk-in-0002", 1, "2026-12-24", "b@example.com").andExpect(status().isCreated());
        assertThat(active(1, "2026-12-24")).isEqualTo(6);   // six guests holding five rooms
    }

    @Test
    void theApiJobOnTwoServersGivesItBackOnce() throws Exception {
        fiveHoldsOneOfThemDue();
        int[] expired = new int[2];
        try (var servers = Executors.newVirtualThreadPerTaskExecutor()) {
            servers.submit(() -> expired[0] = holds.expireDue());
            servers.submit(() -> expired[1] = holds.expireDue());
        }
        assertThat(expired[0] + expired[1]).isEqualTo(1);
        assertThat(held(1, "2026-12-24")).isEqualTo(4);
        hold("walk-in-0001", 1, "2026-12-24", "a@example.com").andExpect(status().isCreated());
        hold("walk-in-0002", 1, "2026-12-24", "b@example.com").andExpect(status().isConflict());
        assertThat(active(1, "2026-12-24")).isEqualTo(5);
    }
}
