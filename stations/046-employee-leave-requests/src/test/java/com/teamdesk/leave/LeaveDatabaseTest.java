package com.teamdesk.leave;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.LocalDate;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The tables' rules with Java bypassed, a rollback across both rows, and approvals racing each other. */
class LeaveDatabaseTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    void insert(long employee, String start, String end, int days, String status) {
        jdbc.sql("INSERT INTO leave_requests (employee_id, start_date, end_date, days, reason, status) VALUES (?, ?::date, ?::date, ?, 'Test', ?)")
                .params(employee, start, end, days, status).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        assertThatThrownBy(() -> jdbc.sql("UPDATE employees SET balance_days = -1 WHERE id = 1").update()).hasMessageContaining("employees_balance_not_negative");
        assertThatThrownBy(() -> insert(99, "2026-11-06", "2026-11-10", 3, "PENDING")).hasMessageContaining("leave_requests_employee_fk");
        assertThatThrownBy(() -> insert(1, "2026-11-10", "2026-11-06", 3, "PENDING")).hasMessageContaining("leave_requests_dates_ordered");
        assertThatThrownBy(() -> insert(1, "2026-11-06", "2026-11-10", 0, "PENDING")).hasMessageContaining("leave_requests_days_range");
        assertThatThrownBy(() -> insert(1, "2026-11-06", "2026-11-10", 6, "PENDING")).hasMessageContaining("leave_requests_days_fit_dates");
        assertThatThrownBy(() -> insert(1, "2026-11-06", "2026-11-10", 3, "MAYBE")).hasMessageContaining("leave_requests_status_known");
    }

    @Test
    void whenTheBalanceWriteFailsTheApprovalRollsBackToo() throws Exception {
        long id = newRequest(2, "2026-11-06", "2026-11-10");   // 3 days; Rohan has 2
        // Skip the Java balance check: the database refuses -1, and the request's change goes with it.
        assertThatThrownBy(() -> transaction.executeWithoutResult(status -> requests.findWithEmployeeById(id).orElseThrow().approve()))
                .hasMessageContaining("employees_balance_not_negative");
        assertThat(statusInTheDatabase(id)).isEqualTo("PENDING");
        assertThat(balanceInTheDatabase(2)).isEqualTo(2);
    }

    @Test
    void eightManagersApprovingTheSameRequestDeductOnce() throws Exception {
        long id = newRequest(1, "2026-11-06", "2026-11-10");
        List<Integer> statuses = together(8, () -> approve(id).andReturn().getResponse().getStatus());
        assertThat(statuses).filteredOn(s -> s == 200).hasSize(1);
        assertThat(statuses).filteredOn(s -> s == 409).hasSize(7);
        assertThat(balanceInTheDatabase(1)).isEqualTo(9);
    }

    @Test
    void approvingDifferentRequestsAtOnceNeverLosesADeduction() throws Exception {
        AtomicInteger next = new AtomicInteger();
        long[] ids = new long[6];
        for (int i = 0; i < ids.length; i++) {   // six Mon-Wed requests (3 days each) from Asha, who has 12: four fit
            LocalDate monday = LocalDate.of(2026, 11, 2).plusWeeks(i);
            ids[i] = newRequest(1, monday.toString(), monday.plusDays(2).toString());
        }
        List<Integer> statuses = together(ids.length, () -> approve(ids[next.getAndIncrement()]).andReturn().getResponse().getStatus());
        assertThat(statuses).isSubsetOf(200, 409, 422);   // a 409 means "reload and retry", never a lost deduction
        long approved = jdbc.sql("SELECT count(*) FROM leave_requests WHERE status = 'APPROVED'").query(Long.class).single();
        assertThat(approved).isEqualTo(statuses.stream().filter(s -> s == 200).count()).isPositive();
        assertThat(balanceInTheDatabase(1)).isEqualTo(12 - 3 * (int) approved);   // every approval's deduction is there
    }
}
