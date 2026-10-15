package com.mediqo.reports;

/** The report's SQL before the fix, kept only in tests: the first version, and two "fixes" that were not enough. */
final class OldReportQueries {

    private OldReportQueries() {
    }

    /** Version 1: INNER JOIN, follow-ups joined row by row, count(*). */
    static final String INNER_JOIN = """
            SELECT d.name, count(*) AS appointments
              FROM doctors d
              JOIN appointments a ON a.doctor_id = d.id
              LEFT JOIN follow_ups f ON f.appointment_id = a.id
             WHERE d.active AND a.starts_at >= :from AND a.starts_at < :to AND a.status <> 'CANCELLED'
             GROUP BY d.name""";

    /** "Fix" 1: LEFT JOIN, but the conditions on appointments are still in WHERE. */
    static final String LEFT_JOIN_FILTERED_IN_WHERE = """
            SELECT d.name, count(a.id) AS appointments
              FROM doctors d
              LEFT JOIN appointments a ON a.doctor_id = d.id
             WHERE d.active AND a.starts_at >= :from AND a.starts_at < :to AND a.status <> 'CANCELLED'
             GROUP BY d.name""";

    /** "Fix" 2: conditions moved to ON, but count(*) counts the empty row a LEFT JOIN makes for a doctor with none. */
    static final String LEFT_JOIN_COUNT_STAR = """
            SELECT d.name, count(*) AS appointments
              FROM doctors d
              LEFT JOIN appointments a ON a.doctor_id = d.id
                    AND a.starts_at >= :from AND a.starts_at < :to AND a.status <> 'CANCELLED'
             WHERE d.active
             GROUP BY d.name""";
}
