package com.mediqo.reports;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.util.List;

/**
 * Appointments per active doctor in a range of India days, every doctor included. Four details make it right:
 * LEFT JOIN keeps doctors with no appointments; the date and status conditions sit in the ON clause, because in
 * WHERE they would throw those doctors out again; count(a.id) counts appointments, where count(*) would count the
 * empty row a LEFT JOIN makes; and follow-ups are counted per appointment first, so joining them cannot repeat rows.
 */
@Repository
class DoctorLoadReport {

    static final ZoneId INDIA = ZoneId.of("Asia/Kolkata");

    record Row(long doctorId, String name, String speciality, long appointments, long completed, long noShows,
               long followUps, long revenuePaise, Integer noShowPercent) {
    }

    private static final String SQL = """
            SELECT d.id AS doctor_id, d.name, d.speciality,
                   count(a.id)                                                  AS appointments,
                   count(a.id) FILTER (WHERE a.status = 'COMPLETED')            AS completed,
                   count(a.id) FILTER (WHERE a.status = 'NO_SHOW')              AS no_shows,
                   coalesce(sum(f.follow_ups), 0)                               AS follow_ups,
                   coalesce(sum(a.fee_paise) FILTER (WHERE a.status = 'COMPLETED'), 0) AS revenue_paise,
                   -- NULLIF turns "divide by 0" into "divide by NULL", which is NULL: no appointments, no rate
                   round(100.0 * count(a.id) FILTER (WHERE a.status = 'NO_SHOW') / nullif(count(a.id), 0))::int AS no_show_percent
              FROM doctors d
              LEFT JOIN appointments a
                     ON a.doctor_id = d.id
                    AND a.starts_at >= :from AND a.starts_at < :to
                    AND a.status <> 'CANCELLED'
              LEFT JOIN (SELECT appointment_id, count(*) AS follow_ups FROM follow_ups GROUP BY appointment_id) f
                     ON f.appointment_id = a.id
             WHERE d.active
             GROUP BY d.id, d.name, d.speciality
            HAVING count(a.id) >= :min
             ORDER BY appointments DESC, d.name""";

    private final JdbcClient jdbc;

    DoctorLoadReport(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    record SpecialityRow(String speciality, long doctors, long appointments) {
    }

    /** count(DISTINCT d.id): after the join, a doctor appears once per appointment. */
    List<SpecialityRow> bySpeciality(LocalDate from, LocalDate to) {
        return jdbc.sql("""
                        SELECT d.speciality, count(DISTINCT d.id) AS doctors, count(a.id) AS appointments
                          FROM doctors d
                          LEFT JOIN appointments a
                                 ON a.doctor_id = d.id
                                AND a.starts_at >= :from AND a.starts_at < :to
                                AND a.status <> 'CANCELLED'
                         WHERE d.active
                         GROUP BY d.speciality
                         ORDER BY appointments DESC, d.speciality""")
                .param("from", from.atStartOfDay(INDIA).toOffsetDateTime())
                .param("to", to.plusDays(1).atStartOfDay(INDIA).toOffsetDateTime())
                .query(SpecialityRow.class).list();
    }

    /** from and to are both included, as India days: midnight at the start of from to midnight after to. */
    List<Row> between(LocalDate from, LocalDate to, int minAppointments) {
        OffsetDateTime start = from.atStartOfDay(INDIA).toOffsetDateTime();
        OffsetDateTime end = to.plusDays(1).atStartOfDay(INDIA).toOffsetDateTime();
        return jdbc.sql(SQL).param("from", start).param("to", end).param("min", minAppointments).query(Row.class).list();
    }
}
