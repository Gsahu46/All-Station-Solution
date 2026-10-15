package com.teamdesk.leave;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.data.jpa.test.autoconfigure.DataJpaTest;
import org.springframework.boot.jdbc.test.autoconfigure.AutoConfigureTestDatabase;
import org.springframework.boot.jpa.test.autoconfigure.TestEntityManager;
import org.springframework.context.annotation.Import;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * A @DataJpaTest: only JPA, on the real PostgreSQL, and every test runs inside one transaction that is rolled back at
 * the end. That transaction keeps every entity managed, which is exactly what the old approval lacked in production.
 */
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)   // keep PostgreSQL, not an in-memory database
@Import(PostgresTestConfig.class)
class LeaveJpaTest {

    @Autowired
    TestEntityManager entities;
    @Autowired
    EmployeeRepository employees;
    @Autowired
    LeaveRequestRepository requests;

    int balanceInTheDatabase(long id) {
        entities.flush();   // send pending changes now; the test's rollback still undoes them afterwards
        return ((Number) entities.getEntityManager().createNativeQuery("SELECT balance_days FROM employees WHERE id = ?1")
                .setParameter(1, id).getSingleResult()).intValue();
    }

    @Test
    void aManagedEntityIsWrittenWithoutSave() {
        Employee asha = employees.findById(1L).orElseThrow();
        asha.deduct(3);   // no save(): dirty checking finds the change at flush
        assertThat(balanceInTheDatabase(1)).isEqualTo(9);
    }

    @Test
    void saveOnAManagedEntityReturnsTheSameObject() {
        Employee asha = employees.findById(1L).orElseThrow();
        assertThat(employees.save(asha)).isSameAs(asha);   // JPA has no update(): save here does nothing at all
    }

    @Test
    void saveOnADetachedEntityReturnsACopyAndOnlyTheCopyIsTracked() {
        Employee asha = employees.findById(1L).orElseThrow();
        entities.detach(asha);
        asha.deduct(3);
        Employee managed = employees.save(asha);   // merge: loads the row and copies asha's fields onto a managed copy
        assertThat(managed).isNotSameAs(asha);
        asha.deduct(5);   // the copy you passed in is still detached: this change goes nowhere
        assertThat(balanceInTheDatabase(1)).isEqualTo(9);
        managed.deduct(1);
        assertThat(balanceInTheDatabase(1)).isEqualTo(8);
    }

    @Test
    void theOldApprovalPassesHereWhichIsHowTheBugShipped() {
        LeaveRequest request = requests.save(new LeaveRequest(employees.findById(1L).orElseThrow(),
                LocalDate.of(2026, 11, 6), LocalDate.of(2026, 11, 10), 3, "Sister's wedding in Jaipur"));
        new OldLeaveDesk(requests).approve(request.getId());
        // Green: the test's own transaction kept the employee managed. DetachedEntityTrapTest runs the same code
        // without one, as production did, and the balance stays at 12.
        assertThat(balanceInTheDatabase(1)).isEqualTo(9);
    }
}
