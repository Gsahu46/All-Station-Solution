package com.mediqo.doctors;

import jakarta.persistence.EntityManagerFactory;
import org.hibernate.SessionFactory;
import org.hibernate.stat.Statistics;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The table's rules with Java bypassed, a rollback, and how many queries a search costs. */
class DoctorDatabaseTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;
    @Autowired
    EntityManagerFactory entityManagerFactory;
    @Autowired
    DoctorDirectory directory;

    void insert(long id, String registration, long salary, long clinic) {
        jdbc.sql("INSERT INTO doctors (id, name, speciality, city, registration_number, personal_phone, salary_paise, clinic_id) VALUES (?, 'Dr Test', 'Neurology', 'Pune', ?, '0', ?, ?)")
                .params(id, registration, salary, clinic).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        assertThatThrownBy(() -> insert(100, "MMC-2011-04512", 1, 1)).hasMessageContaining("doctors_registration_unique");
        assertThatThrownBy(() -> insert(100, "MMC-2099-00001", 1, 9)).hasMessageContaining("doctors_clinic_fk");
        assertThatThrownBy(() -> insert(100, "MMC-2099-00001", 0, 1)).hasMessageContaining("doctors_salary_positive");
    }

    @Test
    void aFailedImportLeavesTheDirectoryAsItWas() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(status -> {
            insert(100, "MMC-2099-00001", 1, 1);
            insert(101, "MMC-2099-00001", 1, 1);   // same registration: the whole import rolls back
        })).hasMessageContaining("doctors_registration_unique");
        assertThat(doctors.count()).isEqualTo(6);
    }

    @Test
    void aSearchLoadsDoctorsAndClinicsInOneQuery() {
        Statistics stats = entityManagerFactory.unwrap(SessionFactory.class).getStatistics();
        stats.clear();
        directory.search(null, null);
        assertThat(stats.getPrepareStatementCount()).isEqualTo(1);   // @EntityGraph: a join, not 1 + one per clinic

        stats.clear();
        transaction.executeWithoutResult(status -> doctors.findAll().forEach(d -> d.getClinic().getName()));
        assertThat(stats.getPrepareStatementCount()).isEqualTo(3);   // without it: 1 for doctors + 1 per clinic (2)
    }
}
