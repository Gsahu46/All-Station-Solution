package com.kartwala.refunds;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.web.ErrorResponseException;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * The service with Mockito, no Spring. Stub the query (OrderLookup: what it returns matters, how often it is called
 * does not), verify the command (EligibilityAudit: that it happened is the behaviour). Strict stubs are on, so a stub
 * the code never uses fails the test.
 */
@ExtendWith(MockitoExtension.class)
class RefundServiceTest {

    // 20:00 UTC on 15 October is 01:30 on 16 October in India.
    static final Clock LATE_EVENING_UTC = Clock.fixed(Instant.parse("2026-10-15T20:00:00Z"), ZoneOffset.UTC);

    @Mock
    OrderLookup orders;
    @Mock
    EligibilityAudit audit;

    RefundService service() {
        return new RefundService(orders, audit, LATE_EVENING_UTC);
    }

    @Test
    void theLastDayIsCountedInIndiaNotOnTheServer() {
        // Delivered 15 September: the 30-day window ends on 15 October. On the server it is still the 15th; in India
        // it is the 16th, and the customer's calendar decides.
        when(orders.find("KW-1001")).thenReturn(Optional.of(
                new Order("KW-1001", "Cotton kurta", Category.CLOTHING, 129_900, LocalDate.of(2026, 9, 15), false)));
        RefundRules.Decision d = service().check("kw-1001", Reason.SIZE_ISSUE, true, null);
        assertThat(d.reasons()).containsExactly("WINDOW_CLOSED");
        assertThat(d.lastDayToReturn()).isEqualTo(LocalDate.of(2026, 10, 15));
    }

    @Test
    void everyDecisionIsRecordedOnce() {
        when(orders.find("KW-1004")).thenReturn(Optional.of(
                new Order("KW-1004", "Smartphone", Category.ELECTRONICS, 1_899_900, LocalDate.of(2026, 10, 14), false)));
        RefundRules.Decision d = service().check("KW-1004", Reason.DAMAGED, null, false);
        ArgumentCaptor<RefundRules.Decision> recorded = ArgumentCaptor.forClass(RefundRules.Decision.class);
        verify(audit).record(eq("KW-1004"), eq(Reason.DAMAGED), recorded.capture());
        assertThat(recorded.getValue()).isEqualTo(d);
        assertThat(d.refundPaise()).isEqualTo(1_899_900);
    }

    @Test
    void anUnknownOrderOrAMissingAnswerRecordsNothing() {
        when(orders.find("KW-9999")).thenReturn(Optional.empty());
        assertThatThrownBy(() -> service().check("KW-9999", Reason.DAMAGED, null, null))
                .isInstanceOfSatisfying(ErrorResponseException.class, e -> assertThat(e.getStatusCode().value()).isEqualTo(404));
        when(orders.find("KW-1004")).thenReturn(Optional.of(
                new Order("KW-1004", "Smartphone", Category.ELECTRONICS, 1_899_900, LocalDate.of(2026, 10, 14), false)));
        assertThatThrownBy(() -> service().check("KW-1004", Reason.DAMAGED, null, null))
                .isInstanceOfSatisfying(ErrorResponseException.class, e -> assertThat(e.getStatusCode().value()).isEqualTo(400));
        verify(audit, never()).record(any(), any(), any());
    }
}
