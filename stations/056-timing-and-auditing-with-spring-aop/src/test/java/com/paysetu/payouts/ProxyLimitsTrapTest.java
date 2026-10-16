package com.paysetu.payouts;

import org.junit.jupiter.api.Test;
import org.springframework.aop.support.AopUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Import;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * The first test written for this station. The audit annotation replaced 120 copies of timing code, and then some
 * methods were still not audited. Each test calls one @Audited method in a different way and counts the events.
 */
@Import(MonthEndReports.class)
class ProxyLimitsTrapTest extends ApiTest {

    @Autowired
    MonthEndReports reports;

    @Test
    void aPublicMethodCalledFromOutsideIsAudited() {
        assertThat(AopUtils.isCglibProxy(reports)).isTrue();
        assertThat(reports.monthly()).isEqualTo("ran");
        assertThat(auditEvents()).isEqualTo(1);
    }

    @Test
    void aSelfInvokedMethodIsNot() {
        assertThat(reports.dailyThenMonthly()).isEqualTo("ran");
        assertThat(auditEvents()).isZero();
    }

    @Test
    void aFinalMethodIsNotAndRunsWithoutItsFields() {
        assertThat(reports.finalReport()).isEqualTo("jdbc was null");   // on the proxy, not on the real bean
        assertThat(auditEvents()).isZero();
    }

    @Test
    void aPrivateMethodIsNot() {
        assertThat(reports.viaPrivate()).isEqualTo("ran");
        assertThat(auditEvents()).isZero();
    }
}
