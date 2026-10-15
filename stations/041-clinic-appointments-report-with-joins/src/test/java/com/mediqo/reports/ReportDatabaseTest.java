package com.mediqo.reports;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.LocalDate;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/** The data's rules with Java bypassed, and a rollback that leaves the report as it was. */
class ReportDatabaseTest extends ApiTest {

    @Autowired
    TransactionTemplate transaction;

    void appointment(long doctor, String status, long fee) {
        jdbc.sql("INSERT INTO appointments (doctor_id, patient_name, starts_at, status, fee_paise) VALUES (?, 'Test', TIMESTAMPTZ '2026-10-07 10:00 Asia/Kolkata', ?, ?)")
                .params(doctor, status, fee).update();
    }

    @Test
    void namedConstraintsHoldWithoutJava() {
        assertThatThrownBy(() -> appointment(99, "BOOKED", 100)).hasMessageContaining("appointments_doctor_fk");
        assertThatThrownBy(() -> appointment(4, "MAYBE", 100)).hasMessageContaining("appointments_status_known");
        assertThatThrownBy(() -> appointment(4, "BOOKED", -1)).hasMessageContaining("appointments_fee_not_negative");
        assertThatThrownBy(() -> jdbc.sql("INSERT INTO follow_ups (appointment_id, due_on, reason) VALUES (999, CURRENT_DATE, 'x')").update())
                .hasMessageContaining("follow_ups_appointment_fk");
    }

    @Test
    void aRolledBackDayOfAppointmentsNeverReachesTheReport() {
        assertThatThrownBy(() -> transaction.executeWithoutResult(status -> {
            appointment(4, "COMPLETED", 90000);
            appointment(4, "COMPLETED", -90000);   // refused: the whole day's import is rolled back
        })).hasMessageContaining("appointments_fee_not_negative");
        assertThat(report.between(LocalDate.parse(FROM), LocalDate.parse(TO), 0))
                .filteredOn(r -> r.name().equals("Dr Khan")).singleElement()
                .extracting(DoctorLoadReport.Row::appointments).isEqualTo(0L);
    }
}
