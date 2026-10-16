package com.paysetu.payouts;

import org.springframework.jdbc.core.simple.JdbcClient;

/**
 * A test-only bean with @Audited methods called in each of the ways that matter. The trap test registers it, so
 * Spring proxies it exactly as it would a service.
 */
class MonthEndReports {

    private final JdbcClient jdbc;

    MonthEndReports(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Audited(action = "REPORT_RUN")
    public String monthly() {
        return "ran";
    }

    /** Self-invocation: "this.monthly()", past the proxy. */
    public String dailyThenMonthly() {
        return monthly();
    }

    /** Final: the proxy cannot override it, so it runs on the proxy object itself, whose fields were never set. */
    @Audited(action = "REPORT_RUN")
    public final String finalReport() {
        return jdbc == null ? "jdbc was null" : "ran";
    }

    public String viaPrivate() {
        return privateReport();
    }

    /** Private: a proxy cannot see it at all. */
    @Audited(action = "REPORT_RUN")
    private String privateReport() {
        return "ran";
    }
}
