package com.mediqo.reports;

import org.junit.jupiter.api.Test;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.Map;
import java.util.stream.Collectors;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.entry;

/** The first test written for this station: the old SQL against the demo week, then the two half-fixes. */
class InnerJoinTrapTest extends ApiTest {

    Map<String, Long> run(String sql) {
        OffsetDateTime from = LocalDate.parse(FROM).atStartOfDay(DoctorLoadReport.INDIA).toOffsetDateTime();
        OffsetDateTime to = LocalDate.parse(TO).plusDays(1).atStartOfDay(DoctorLoadReport.INDIA).toOffsetDateTime();
        return jdbc.sql(sql).param("from", from).param("to", to)
                .query((rs, n) -> Map.entry(rs.getString("name"), rs.getLong("appointments"))).list().stream()
                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
    }

    @Test
    void theOldReportHidesDrKhanAndCountsDrMehtasFollowUpsAsAppointments() {
        Map<String, Long> old = run(OldReportQueries.INNER_JOIN);
        assertThat(old).doesNotContainKey("Dr Khan");                // INNER JOIN: no appointments, no row
        assertThat(old).contains(entry("Dr Mehta", 4L));             // 3 appointments; the one with 2 follow-ups counted twice
    }

    @Test
    void aLeftJoinWithTheDateInWhereHidesHimAgain() {
        assertThat(run(OldReportQueries.LEFT_JOIN_FILTERED_IN_WHERE)).doesNotContainKey("Dr Khan");   // NULL >= date is not true
    }

    @Test
    void aLeftJoinWithCountStarGivesHimAnAppointmentHeNeverHad() {
        assertThat(run(OldReportQueries.LEFT_JOIN_COUNT_STAR)).contains(entry("Dr Khan", 1L));
    }

    @Test
    void theReportCountsEveryDoctorCorrectly() {
        Map<String, Long> now = report.between(LocalDate.parse(FROM), LocalDate.parse(TO), 0).stream()
                .collect(Collectors.toMap(DoctorLoadReport.Row::name, DoctorLoadReport.Row::appointments));
        assertThat(now).containsExactlyInAnyOrderEntriesOf(Map.of("Dr Mehta", 3L, "Dr Iyer", 2L, "Dr Rao", 1L, "Dr Khan", 0L));
    }
}
