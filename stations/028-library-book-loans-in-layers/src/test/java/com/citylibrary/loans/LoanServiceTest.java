package com.citylibrary.loans;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * The rules alone: no Spring, no HTTP, no store. The repositories are Mockito mocks, so each test says exactly what
 * the store contains and checks exactly what the service saves. Runs in milliseconds.
 */
@ExtendWith(MockitoExtension.class)
class LoanServiceTest {

    @Mock
    Repositories.MemberRepository members;
    @Mock
    Repositories.BookRepository books;
    @Mock
    Repositories.LoanRepository loans;

    final Clock oct14 = Clock.fixed(Instant.parse("2026-10-14T05:00:00Z"), ZoneId.of("Asia/Kolkata"));
    final Model.Member asha = new Model.Member("m-1", "Asha", "CL-0001", 0);
    final Model.Book book = new Model.Book("b-1", "Malgudi Days", "LIB100001");

    LoanService service() {
        return new LoanService(members, books, loans, oct14);   // constructor injection makes this one line
    }

    static Model.Loan active(String id) {
        return new Model.Loan(id, "m-1", "b-" + id, LocalDate.of(2026, 10, 1), LocalDate.of(2026, 10, 15), null, 0);
    }

    @Test
    void aRefusedLoanIsNeverSaved() {
        when(members.findById("m-1")).thenReturn(Optional.of(asha));
        when(books.findById("b-1")).thenReturn(Optional.of(book));
        when(loans.findByMember("m-1")).thenReturn(List.of(active("x"), active("y"), active("z")));
        assertThatThrownBy(() -> service().borrow("m-1", "b-1"))
                .isInstanceOfSatisfying(LoanService.Refused.class, e -> assertThat(e.reason).isEqualTo(LoanService.Reason.LIMIT_REACHED));
        verify(loans, never()).save(any());
    }

    @Test
    void anAllowedLoanIsSavedDueInFourteenDays() {
        when(members.findById("m-1")).thenReturn(Optional.of(asha));
        when(books.findById("b-1")).thenReturn(Optional.of(book));
        when(loans.findByMember("m-1")).thenReturn(List.of(active("x"), active("y")));   // 2 out: one more is fine
        when(loans.findActiveByBook("b-1")).thenReturn(Optional.empty());
        service().borrow("m-1", "b-1");
        ArgumentCaptor<Model.Loan> saved = ArgumentCaptor.forClass(Model.Loan.class);
        verify(loans).save(saved.capture());
        assertThat(saved.getValue().dueOn()).isEqualTo(LocalDate.of(2026, 10, 28));
    }

    @Test
    void aLateReturnAddsTheFineToTheMember() {
        Model.Loan due10th = new Model.Loan("l-1", "m-1", "b-1", LocalDate.of(2026, 9, 26), LocalDate.of(2026, 10, 10), null, 0);
        when(loans.findById("l-1")).thenReturn(Optional.of(due10th));
        when(members.findById("m-1")).thenReturn(Optional.of(asha));
        assertThat(service().giveBack("l-1").finePaise()).isEqualTo(4 * 500);   // 4 days late on 14 October
        verify(members).save(asha.withFine(2_000));
    }
}
